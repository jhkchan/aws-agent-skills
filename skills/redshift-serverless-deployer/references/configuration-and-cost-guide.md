# Configuration and Cost Guide — Redshift Serverless Deployer

Deep reference on encryption strategy, VPC networking, usage-limit
tuning, snapshot and cross-Region DR strategy, Data API patterns,
query editor v2 setup, the full NEVER list, edge-case handling, and
pre-flight safety CLI.

## Encryption strategy

### Customer-managed key (CMK) — recommended for production

| Aspect | Detail |
|---|---|
| Key type | Symmetric (AES-256-GCM). NEVER asymmetric for Redshift. |
| Key policy | MUST allow `redshift-serverless.amazonaws.com` to `kms:Encrypt`, `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`, `kms:CreateGrant`, `kms:DescribeKey`. |
| Rotation | Enable annual rotation via `aws kms enable-key-rotation`. |
| Cross-account | Add the consumer account root to the key policy with `kms:Decrypt` and `kms:DescribeKey`. |
| Audit | CloudTrail logs every `kms:Decrypt` call with the namespace ARN. |

### AWS-owned key — default, NOT recommended for production

| Aspect | Detail |
|---|---|
| Visibility | Not visible in your KMS console. Cannot be audited via CloudTrail. |
| Rotation | Managed by AWS; no user control. |
| Cross-Region snapshots | NOT supported. Cross-Region snapshot copy requires a CMK. |
| Cross-account | NOT supported. Cannot share data encrypted with AWS-owned key across accounts. |

**NEVER create a production namespace with the AWS-owned key.** The
only way to switch keys after creation is a full UNLOAD/LOAD cycle,
which means hours of downtime and a secondary namespace.

### Key policy template (CMK)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "redshift-serverless.amazonaws.com"},
      "Action": [
        "kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*",
        "kms:GenerateDataKey*", "kms:CreateGrant", "kms:DescribeKey"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<account-id>:root"},
      "Action": "kms:*",
      "Resource": "*"
    }
  ]
}
```

## VPC networking deep dive

### Why enhanced VPC routing matters

Without enhanced VPC routing, Redshift Serverless COPY/UNLOAD
operations traverse the public internet via Amazon S3 endpoints. This
violates compliance regimes (HIPAA, PCI-DSS, SOC 2) and bypasses VPC
flow logs.

With enhanced VPC routing:
- **COPY/UNLOAD traffic stays in the VPC** via S3 VPC gateway endpoints
  or interface endpoints.
- **VPC flow logs capture the traffic.**
- **Security group egress rules apply** — you can restrict which S3
  buckets the workgroup can reach.

### Subnet group requirements

- **Minimum 3 subnets** across different AZs for high availability.
- **Private IP ranges** if public access is disabled (recommended).
- **Each subnet MUST have at least /27 mask** (16+ free IPs) to
  accommodate Redshift Serverless ENIs.

### Security group rules

| Direction | Port | Source / Destination | Purpose |
|---|---|---|---|
| Inbound | 5439 | Analytics app SG | JDBC/ODBC queries |
| Inbound | 5439 | Lambda SG (if Data API via Lambda) | Data API (uses port internally) |
| Outbound | 443 | S3 VPC endpoint | COPY/UNLOAD with enhanced VPC routing |
| Outbound | 443 | Glue VPC endpoint | Glue catalog access |

**NEVER set inbound source to `0.0.0.0/0`.** A data warehouse should
never be reachable from the public internet.

### Public access toggle

| `publicly-accessible` | Behavior |
|---|---|
| `true` | Workgroup gets a public IP. Reachable from the internet if SG allows. NEVER for production. |
| `false` | Workgroup gets a private IP only. Reachable via VPC peering, Transit Gateway, VPN, or Direct Connect. Recommended. |

## Usage-limit tuning

### The 80/20 budget rule

- **Daily limit = 80% of daily budget.** Catches runaway queries early
  with `breach-action=log`.
- **Monthly limit = 120% of monthly budget.** Hard ceiling with
  `breach-action=emit-metric` + CloudWatch alarm.

### RPU-hour estimation

| Workload | Peak concurrency | Avg query duration | Estimated daily RPU-hours |
|---|---|---|---|
| BI dashboard (10 users) | 5-10 queries | 30-60s | 50-150 |
| Ad-hoc analytics (20 users) | 10-20 queries | 60-300s | 200-500 |
| Heavy ETL (nightly 4h window) | 5-10 queries | 600-1800s | 300-800 |
| Multi-tenant SaaS (100 tenants) | 20-50 queries | 30-120s | 500-1500 |

### Breach action matrix

| `breach_action` | Production | Dev/test | DR |
|---|---|---|---|
| `log` | Recommended (daily limit) | OK | OK |
| `emit-metric` | Recommended (monthly limit) | OK | OK |
| `disable` | NEVER without runbook | OK (cap cost) | NEVER |

### CloudWatch alarm template

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name redshift-rpu-budget-near \
  --metric-name ServerlessComputeCapacity \
  --namespace AWS/Redshift \
  --statistic Sum \
  --period 3600 \
  --threshold 450 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=Workgroup,Value=<workgroup> \
  --alarm-actions arn:aws:sns:<region>:<account-id>:redshift-alerts
```

## Snapshot and cross-Region DR strategy

### Snapshot intervals and cost

| Interval | RPO | Snapshot storage cost | Use case |
|---|---|---|---|
| 1 hour | 1 hour | 24x daily snapshots | Critical, low-RPO |
| 8 hours (default) | 8 hours | 3x daily snapshots | Standard production |
| 24 hours | 24 hours | 1x daily snapshot | Dev/test |

Each snapshot consumes storage at the source Region AND the
destination Region (if cross-Region copy is enabled).

### Cross-Region snapshot copy architecture

```
Source Region (us-east-1)                 Destination Region (us-west-2)
┌─────────────────────┐                   ┌─────────────────────┐
│  Redshift Namespace │                   │  DR Namespace       │
│  (analytics-ns-prod)│                   │  (analytics-ns-dr)  │
│                     │   scheduled copy  │                     │
│  CMK: redshift-prod │ ────────────────> │  CMK: redshift-dr   │
│  (us-east-1)        │                   │  (us-west-2)        │
└─────────────────────┘                   └─────────────────────┘
        │                                          │
        v                                          v
  Snapshot copy grant                       Snapshot copy grant
  (configured on source)                    (referenced by source)
```

Rules:
- **Destination CMK is in a DIFFERENT Region.** NEVER reuse the
  source-Region key — KMS keys are Region-scoped.
- **Snapshot copy grant** is created in the destination Region and
  referenced by the source namespace via `snapshot-copy-configurations`.
- **Retention period** controls how long snapshots survive in the
  destination Region. Default is the source retention; override
  explicitly.

### DR failover procedure

1. Identify the latest successful cross-Region snapshot.
2. In the destination Region, run `restore-from-snapshot` to create a
   new namespace.
3. Create a workgroup attached to the restored namespace.
4. Update application connection strings to the DR workgroup endpoint.
5. RTO: 30-90 minutes depending on snapshot size and RPU capacity.

## Data API patterns

### Pattern 1: Lambda query (async)

```python
import boto3, json, time

redshift = boto3.client('redshift-data')

def run_query(sql, workgroup, database):
    response = redshift.execute_statement(
        WorkgroupName=workgroup,
        Database=database,
        SecretArn='arn:aws:secretsmanager:...',
        Sql=sql
    )
    statement_id = response['Id']

    # Poll for completion
    while True:
        status = redshift.describe_statement(Id=statement_id)
        if status['Status'] in ['FINISHED', 'FAILED', 'ABORTED']:
            break
        time.sleep(2)

    if status['Status'] == 'FINISHED':
        result = redshift.get_statement_result(Id=statement_id)
        return result['Records']
    raise Exception(f"Query {status['Status']}: {status.get('Error')}")
```

### Pattern 2: Step Functions batch

Use Step Functions with the `redshift-data` service integration. The
`describe-statement` poll loop is a native `Task` with
`Retry` on `Status=SUBMITTED|STARTED`.

### Data API limitations

- **Max result set:** 100 MB per `get-statement-result` call. Paginate
  with `NextToken`.
- **Max query duration:** 24 hours (configurable via
  `max_query_execution_time` config-parameter).
- **Concurrency:** 200 concurrent Data API queries per account per
  Region (soft quota).
- **Latency:** NOT for OLTP. The API round-trip is 200-500ms even for
  trivial queries.

**NEVER use the Data API for high-frequency OLTP queries.** It is
optimized for batch analytics and Lambda/Step Functions integrations.

## Query editor v2 setup

### IAM policy

The IAM principal running the query editor v2 needs:

- `redshift-serverless:DescribeWorkgroup`,
  `redshift-serverless:ListWorkgroups`,
  `redshift-serverless:GetCredentials`
- `redshift-data:ExecuteStatement`, `DescribeStatement`,
  `GetStatementResult`, `ListStatements`, `CancelStatement`
- `secretsmanager:GetSecretValue` on the admin secret ARN (if using
  Secrets Manager auth)
- `logs:FilterLogEvents` on `/aws/redshift/*` (for log viewing)

### Managed policy

AWS provides a managed policy
`AmazonRedshiftQueryEditorV2FullAccess`. For least privilege, write a
custom inline policy scoped to the specific workgroup and secret.

## Full NEVER list (12 items)

1. NEVER create a production namespace with the AWS-owned KMS key.
2. NEVER enable `publicly-accessible=true` on a production workgroup.
3. NEVER deploy without `enhanced_vpc_routing=true` if you COPY/UNLOAD.
4. NEVER set `breach-action=disable` on production usage limits without
   a runbook.
5. NEVER delete the cross-Region snapshot CMK while a copy grant
   references it.
6. NEVER set inbound security group source to `0.0.0.0/0` for port 5439.
7. NEVER hardcode the admin password in create-namespace CLI. Use
   Secrets Manager.
8. NEVER use the Data API for high-frequency OLTP queries.
9. NEVER create a subnet group with fewer than 3 AZs.
10. NEVER reuse the source-Region CMK for cross-Region snapshot copy.
11. NEVER skip log exports (`userlog`, `connectionlog`,
    `useractivitylog`) at namespace creation — they are not retroactive.
12. NEVER forget to set CloudWatch log group retention — Redshift
    Serverless creates the log group with `Never Expire` if not
    pre-configured.

## Edge-case handling

### Migrating from provisioned Redshift to Serverless

1. Take a final snapshot of the provisioned cluster.
2. Create a Serverless namespace.
3. Restore from the snapshot into the new namespace.
4. Database objects and data transfer; cluster parameter groups do NOT
   transfer (Serverless uses config-parameters on the workgroup).
5. Update application connection strings.

### Cross-account data sharing (datashares)

- Producer creates a datashare and grants access to the consumer
  account.
- Consumer creates a namespace and references the datashare.
- NEVER share the namespace IAM role across accounts.

### Zero-ETL from Aurora

- Configured at the Aurora cluster, not the Redshift namespace.
- Aurora cluster needs a `redshift.amazonaws.com` role to push data.
- Replication lag is typically seconds.
- Target namespace MUST exist before configuring zero-ETL.

### Secrets Manager rotation

- Managed rotation Lambda runs every 30 days by default.
- Rotation updates BOTH the secret AND the namespace admin password
  atomically.
- Override rotation schedule via
  `aws secretsmanager rotate-secret --rotation-rules`.

### Usage limit reset

- When `breach-action=disable` triggers, the workgroup stays disabled
  until the next billing period OR until you manually delete the usage
  limit.
- To re-enable: `aws redshift-serverless delete-usage-limit --usage-type
  serverless-compute --period monthly` then re-create with a higher
  amount.

## Pre-flight safety CLI

```bash
# 1. KMS key policy
aws kms get-key-policy --key-id alias/redshift-prod --policy-name default

# 2. Subnet group AZ coverage
aws redshift-serverless describe-subnet-groups --subnet-group-name <subnet-group> \
  --query 'subnetGroups[0].subnets[*].availabilityZone'

# 3. Security group inbound rules
aws ec2 describe-security-groups --group-ids sg-redshift-prod \
  --query 'SecurityGroups[0].IpPermissions'

# 4. Namespace IAM role trust
aws iam get-role --role-name <namespace-role> \
  --query 'Role.AssumeRolePolicyDocument.Statement[?Principal.Service==`redshift.amazonaws.com`]'

# 5. Secrets Manager secret
aws secretsmanager describe-secret --secret-id <secret-id>

# 6. Service quota
aws service-quotas get-service-quota \
  --service-code redshift-serverless \
  --quota-code L-XXXXXXXX

# 7. Cross-Region destination CMK
aws kms describe-key --key-id alias/redshift-dr --region <dest-region>

# 8. Existing namespace config (for rollback)
aws redshift-serverless get-namespace --namespace-name <namespace> > /tmp/ns-backup.json
aws redshift-serverless get-workgroup --workgroup-name <workgroup> > /tmp/wg-backup.json
```
