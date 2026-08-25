---
name: redshift-serverless-deployer
description: 'Deploys Amazon Redshift Serverless with production-grade configuration: namespace creation (DB name, admin credentials, KMS encryption, IAM roles, VPC security groups), workgroup creation (base capacity RPU, subnet group, public access, enhanced VPC routing), usage limits (daily/monthly RPU caps, cost controls), Data API for query execution without persistent connections, query editor v2, scheduled and cross-Region snapshots for DR, and latest features (cross-Region snapshot copy, cost controls with usage thresholds, Secrets Manager integration, zero-ETL). Emits a READY_TO_DEPLOY checklist with every configuration item verified. Use when creating a Redshift Serverless namespace or workgroup, validating a configuration, or generating deployment CLI and IaC templates. Triggers: Redshift Serverless, serverless data warehouse, RPU capacity, namespace, workgroup, Data API, cross-Region snapshots, usage limits, cost controls, query editor v2.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with redshift-serverless, ec2, kms, iam, secretsmanager, and logs access. Works with Terraform aws_redshiftserverless_* resources, CloudFormation AWS::RedshiftServerless::* resources, and the AWS Console Redshift Serverless wizard.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, redshift, redshift-serverless, cloudops, deploy, analytics, namespace, workgroup
  dependencies: aws-orchestrator
  keywords: aws, redshift, redshift-serverless, cloudops, deploy, provisioning, analytics, data-warehouse, namespace, workgroup, rpu, data-api, cross-region-snapshots, usage-limits, cost-controls, kms-encryption
  when_to_use: Invoke when the user wants to create a new Redshift Serverless namespace or workgroup, deploy a serverless data warehouse, validate an existing Redshift Serverless configuration against best practices, generate deployment CLI commands or IaC templates, or troubleshoot a Redshift Serverless deployment failure caused by missing prerequisites (KMS key, security groups, subnet group, IAM roles). Do NOT invoke for provisioned Redshift clusters (use redshift-cluster-deployer), Athena (use athena-query-optimizer), or Aurora (use rds-instance-deployer).
---

# Redshift Serverless Deployer

An AWS CloudOps agent skill that deploys Amazon Redshift Serverless
namespaces and workgroups with correct production defaults. Emits a
READY_TO_DEPLOY checklist verifying every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why the namespace-before-workgroup order matters | "Reasoning framework" |
| What to verify before deploying | "Prerequisites" |
| The ordered deployment steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| Workload-type decision matrix | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/cli-commands-and-iac.md` |
| Security, networking, cost controls, full NEVER | `references/configuration-and-cost-guide.md` |

## STRICT output contract

When this skill is invoked with a Redshift Serverless deployment
request, the agent MUST respond with the READY_TO_DEPLOY checklist
defined in "Output format" using the literal all-caps labels
`WORKGROUP:`, `VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`.
Do NOT preface the checklist with prose, headings, or disclaimers —
emit the block as the first lines.

### Required output structure

1. `WORKGROUP: <workgroup-name>` — the Redshift Serverless workgroup
   being deployed.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented
   `aws redshift-serverless ...` commands.

### FORBIDDEN output patterns

- **No prose preamble before `WORKGROUP:`** — first non-empty line
  MUST be `WORKGROUP:`.
- **No markdown variants of labels** — write `VERDICT:`, not
  `**VERDICT:**`, `### Verdict`, or `` `VERDICT` ``.
- **No swapping verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`.
- **No omitting `VERIFICATION_COMMANDS:`** — include even when
  PREREQUISITES_MISSING.
- **No extra sections after `VERIFICATION_COMMANDS:`** — the
  checklist block is the entire response.
- **No status marker drift** — use only `[✓]`, `[✗]`, `[OPTIONAL]`,
  `[INPUT NEEDED]`.

### Perfect example (copy the shape exactly)

```text
WORKGROUP: analytics-wg-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Namespace — analytics-ns-prod, database dev, admin user admin
  [✓]      Admin credentials — stored in Secrets Manager secret arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift/admin-XXX
  [✓]      KMS encryption — customer-managed key arn:aws:kms:us-east-1:123456789012:key/abc123 (encryption enabled)
  [✓]      IAM roles — sysid:aws-redshift arn:aws:iam::123456789012:role/RedshiftNSRole
  [✓]      VPC security groups — sg-redshift-prod (inbound 5439 from sg-analytics-app)
  [✓]      Workgroup — analytics-wg-prod, base capacity 128 RPU
  [✓]      Subnet group — redshift-subnet-group (3 subnets across us-east-1a/b/c)
  [✓]      Public access — disabled (private only)
  [✓]      Enhanced VPC routing — enabled (traffic stays in VPC)
  [✓]      Usage limits — daily 500 RPU-hours, monthly 12000 RPU-hour budget
  [✓]      Data API — enabled (query via execute-statement, no persistent connection)
  [✓]      Query editor v2 — associated (managed IAM policy)
  [✓]      Snapshots — automated every 8 hours, 7-day retention, cross-Region copy to us-west-2 with KMS key arn:aws:kms:us-west-2:123456789012:key/def456
  [OPTIONAL] Concurrency scaling — enabled (auto-scaling beyond base RPU)
VERIFICATION_COMMANDS:
  aws redshift-serverless describe-workgroup --workgroup-name analytics-wg-prod
  aws redshift-serverless describe-namespace --namespace-name analytics-ns-prod
  aws redshift-serverless list-usage-limits --usage-type serverless-compute
  aws redshift-serverless describe-scheduled-actions
  aws secretsmanager describe-secret --secret-id redshift/admin
  aws kms describe-key --key-id alias/redshift-prod
```

## Reasoning framework (why the deployment order matters)

1. **Namespace FIRST** — a namespace is the database container. It
   owns the database name, admin credentials, KMS key, IAM roles, VPC
   security groups, and snapshot schedule. Without a namespace you
   cannot create a workgroup. The create-namespace call is the only
   place where admin credentials, KMS, and IAM roles are set.
2. **Admin credentials** — choose between Secrets Manager-managed
   (recommended) or manual admin password. Secrets Manager auto-rotates
   and avoids hardcoding secrets. Manual passwords expire after a
   configured period; rotation is YOUR responsibility.
3. **KMS encryption** — Redshift Serverless uses an AWS-owned key by
   default. For production, use a customer-managed key (CMK) so you
   control rotation policy and cross-account access. The CMK must
   exist BEFORE create-namespace.
4. **VPC security groups on the namespace** — the namespace-level
   security groups control which clients can reach the database on port
   5439. A common mistake is to attach a security group with no inbound
   rule, then wonder why the Data API times out.
5. **Workgroup SECOND** — the workgroup attaches to a namespace and
   defines the compute (base capacity RPU), subnet group, public access
   toggle, and enhanced VPC routing. A workgroup without enhanced VPC
   routing sends COPY/UNLOAD traffic over the public internet.
6. **Usage limits THIRD** — Redshift Serverless bills by RPU-hour. A
   runaway query can exhaust a budget in hours. Set daily and monthly
   limits BEFORE the first workload runs.
7. **Snapshots LAST** — configure scheduled snapshots and cross-Region
   copy as the final step so the namespace has data to snapshot.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **KMS key (if CMK encryption)** | CMK must exist and the caller needs `kms:CreateGrant`. NEVER create with AWS-owned and migrate later. | `aws kms describe-key --key-id <alias>` |
| **VPC subnets (3+ AZs)** | Redshift Serverless requires a subnet group spanning at least 3 AZs for HA. | `aws ec2 describe-subnets --subnet-ids <ids>` |
| **Security group(s)** | Inbound rule for port 5439 from the analytics application SG. NEVER `0.0.0.0/0`. | `aws ec2 describe-security-groups --group-ids <sg-ids>` |
| **Subnet group** | Created from the subnets; attached to the workgroup. | `aws redshift-serverless describe-subnet-groups` (errors if none) |
| **IAM namespace role (optional)** | Trust `redshift.amazonaws.com`. Scoped for S3/Glue/KMS access during COPY/UNLOAD. | `aws iam get-role --role-name <role>` |
| **Secrets Manager secret (recommended)** | Stores admin password. Auto-rotation via Lambda. NEVER hardcode admin password in create-namespace. | `aws secretsmanager describe-secret --secret-id <id>` |
| **Service quota** | Default 30 RPU-hours per region per account. Request increase BEFORE production. | `aws service-quotas get-service-quota --service-code redshift-serverless --quota-code L-XXXXXXXX` |
| **Cross-Region KMS key (if cross-Region snapshots)** | Snapshot copy requires a separate CMK in the destination Region. NEVER reuse the source-Region key. | `aws kms describe-key --key-id <dest-alias> --region <dest-region>` |

## Deployment procedure (apply in order)

### Step 1: KMS key (encryption)

For production, use a customer-managed key. The AWS-owned key cannot
be audited, rotated, or shared cross-account. Create the CMK BEFORE
the namespace.

```bash
aws kms create-key --description "Redshift Serverless production key" \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {"Service": "redshift-serverless.amazonaws.com"},
        "Action": ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:CreateGrant", "kms:DescribeKey"],
        "Resource": "*"
      }
    ]
  }'

aws kms create-alias --alias-name alias/redshift-prod \
  --target-key-id <key-id>
```

Rules:
- **Key policy MUST allow `redshift-serverless.amazonaws.com`** to use
  `kms:CreateGrant` and `kms:GenerateDataKey*`.
- **NEVER use the same CMK across Regions** — KMS keys are Region-scoped.
- **Document the key ID** — there is no way to recover the key ID from
  a namespace after creation if the alias is deleted.

### Step 2: Subnet group

```bash
aws redshift-serverless create-subnet-group \
  --subnet-group-name redshift-subnet-group \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --security-group-ids sg-redshift-prod
```

Rules:
- **At least 3 subnets** across different AZs for high availability.
- **Subnets MUST be in private IP ranges** if you disable public access
  (recommended for production).
- **Security group inbound** MUST allow port 5439 from the analytics
  application SG. NEVER `0.0.0.0/0`.

### Step 3: IAM namespace role (for COPY/UNLOAD/S3/Glue)

The namespace IAM role is assumed by Redshift Serverless for
data-plane AWS API calls (COPY from S3, UNLOAD to S3, Glue catalog
integration). Without it, COPY from S3 fails with `S3ServiceException`.

```bash
aws iam create-role \
  --role-name RedshiftNSRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "redshift.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name RedshiftNSRole \
  --policy-name redshift-data-access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject", "s3:ListBucket"],
        "Resource": ["arn:aws:s3:::ingest-bucket", "arn:aws:s3:::ingest-bucket/*"]
      },
      {
        "Effect": "Allow",
        "Action": ["s3:PutObject"],
        "Resource": "arn:aws:s3:::unload-bucket/*"
      },
      {
        "Effect": "Allow",
        "Action": ["glue:GetTable", "glue:GetDatabase", "glue:GetPartitions"],
        "Resource": "*"
      }
    ]
  }'
```

### Step 4: Secrets Manager admin credential (recommended)

```bash
aws secretsmanager create-secret \
  --name redshift/admin \
  --secret-string '{
    "username": "admin",
    "password": "<generate-32-char-strong-password>",
    "engine": "redshift",
    "host": "<filled-after-workgroup-creation>",
    "port": 5439
  }'
```

**NEVER hardcode the admin password in the create-namespace CLI.**
Secrets Manager manages rotation, auditing, and access scoping. If you
must use a manual admin password, set `adminPassword` in
create-namespace and rotate it within 90 days.

### Step 5: Namespace

```bash
aws redshift-serverless create-namespace \
  --namespace-name analytics-ns-prod \
  --admin-username admin \
  --admin-user-password '<password-from-secrets>' \
  --db-name dev \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:key/abc123 \
  --default-iam-role-arn arn:aws:iam::123456789012:role/RedshiftNSRole \
  --iam-roles arn:aws:iam::123456789012:role/RedshiftNSRole \
  --security-group-ids sg-redshift-prod \
  --log-exports userlog connectionlog useractivitylog \
  --tags Environment=production Application=analytics
```

Rules:
- **db-name MUST be lowercase**, 1-64 alphanumeric/underscore. NOT a
  reserved keyword. Default `dev`.
- **admin-user-password MUST be 8-64 chars** with at least one
  uppercase, lowercase, number, and special char.
- **log-exports** — `userlog`, `connectionlog`, `useractivitylog`
  stream to CloudWatch Logs. Set on namespace creation; not retroactive.
- **security-group-ids** — applied at the namespace level. The
  security group inbound rule for port 5439 controls client access.

### Step 6: Workgroup (compute)

```bash
aws redshift-serverless create-workgroup \
  --workgroup-name analytics-wg-prod \
  --namespace-name analytics-ns-prod \
  --base-capacity 128 \
  --subnet-group-name redshift-subnet-group \
  --security-group-ids sg-redshift-prod \
  --publicly-accessible false \
  --config-parameters '[{"parameterKey":"enable_user_activity_logging","parameterValue":"true"},{"parameterKey":"enable_data_api","parameterValue":"true"},{"parameterKey":"enhanced_vpc_routing","parameterValue":"true"},{"parameterKey":"query_group","parameterValue":"analytics"}]' \
  --tags Environment=production Application=analytics
```

Parameters:
- **base-capacity** — RPU (Redshift Processing Units). 8-512 RPU in
  multiples of 8. 128 RPU is a common production starting point.
- **publicly-accessible** — `false` for production. NEVER expose a
  data warehouse to the public internet.
- **enhanced_vpc_routing** — `true` forces COPY/UNLOAD traffic through
  your VPC. Without it, traffic traverses the public internet via
  Amazon S3 endpoints.
- **enable_data_api** — `true` enables the Data API for query
  execution without a persistent JDBC/ODBC connection.

### Step 7: Usage limits (cost controls)

```bash
aws redshift-serverless put-usage-limit \
  --usage-type serverless-compute \
  --amount 500 \
  --period daily \
  --breach-action log

aws redshift-serverless put-usage-limit \
  --usage-type serverless-compute \
  --amount 12000 \
  --period monthly \
  --breach-action emit-metric
```

| `breach-action` | Behavior |
|---|---|
| `log` | Log a CloudWatch event when the limit is exceeded. Queries continue. |
| `emit-metric` | Emit a CloudWatch metric and log. Queries continue. |
| `disable` | Disable the workgroup. ALL queries fail until the limit is reset. |

- **NEVER use `disable` on a production workgroup** without a runbook.
  A threshold breach silently turns off analytics. Use `log` or
  `emit-metric` with a CloudWatch alarm.
- **Daily 500 RPU-hours** is a starting budget for a moderate analytics
  workload. 1 RPU-hour = 1 RPU running for 1 hour.
- **Monitor with CloudWatch:** metric `ServerlessComputeCapacity`,
  dimension `Workgroup`.

### Step 8: Data API

The Data API (enabled via `enable_data_api=true` in the workgroup
config-parameters) lets you execute queries via the
`redshift-data:ExecuteStatement` API. No JDBC/ODBC connection needed.

```bash
aws redshift-data execute-statement \
  --workgroup-name analytics-wg-prod \
  --database dev \
  --sql "SELECT COUNT(*) FROM sales"
```

Rules:
- **The caller needs `redshift-data:ExecuteStatement`** plus the
  Secrets Manager secret permission if using Secrets Manager auth.
- **`describe-statement` and `get-statement-result`** for async result
  retrieval. Long-running queries return immediately with a statement ID.
- **NEVER use the Data API for high-frequency OLTP queries** — it is
  optimized for batch analytics, not microsecond latency.

### Step 9: Query editor v2 association

Query editor v2 is a managed web UI. It requires an IAM policy allowing
`redshift-serverless:*` and `redshift-data:*` for the IAM principal
running it.

```bash
aws iam create-policy \
  --policy-name RedshiftQueryEditorV2Access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "redshift-serverless:DescribeWorkgroup",
          "redshift-serverless:ListWorkgroups",
          "redshift-serverless:ListNamespaces",
          "redshift-data:ExecuteStatement",
          "redshift-data:DescribeStatement",
          "redshift-data:GetStatementResult",
          "redshift-data:ListStatements"
        ],
        "Resource": "*"
      }
    ]
  }'
```

Attach the policy to the IAM user/role that runs the query editor v2.
The query editor auto-discovers workgroups and namespaces.

### Step 10: Snapshots and cross-Region copy

```bash
# Scheduled snapshot
aws redshift-serverless create-scheduled-action \
  --scheduled-action-name analytics-snapshot-schedule \
  --namespace-name analytics-ns-prod \
  --schedule "rate(8 hours)" \
  --target-action '{"CreateSnapshot":{"NamespaceName":"analytics-ns-prod","SnapshotName":"analytics-wg-prod-snapshot"}}' \
  --iam-role arn:aws:iam::123456789012:role/RedshiftNSRole

# Cross-Region snapshot copy
aws redshift-serverless create-namespace \
  --namespace-name analytics-ns-dr \
  ... \
  --no-admin-username \
  --snapshot-copy-grants '[{"DestinationRegion":"us-west-2","KmsKeyId":"arn:aws:kms:us-west-2:123456789012:key/def456"}]'
```

Rules:
- **Cross-Region copy requires a SEPARATE CMK** in the destination
  Region. NEVER reuse the source-Region key — KMS keys are Region-scoped.
- **Snapshot retention** is configurable via the
  `--snapshot-retention-period` on the scheduled action.
- **NEVER delete the cross-Region snapshot CMK** while a snapshot copy
  grant references it — the next scheduled copy will fail silently.

### Step 11: Verification

```bash
aws redshift-serverless describe-workgroup --workgroup-name analytics-wg-prod
aws redshift-serverless describe-namespace --namespace-name analytics-ns-prod
aws redshift-serverless list-usage-limits
aws redshift-serverless describe-scheduled-actions
aws secretsmanager describe-secret --secret-id redshift/admin
aws kms describe-key --key-id alias/redshift-prod
aws logs describe-log-groups --log-group-name-prefix /aws/redshift/analytics-ns-prod
```

## Latest Redshift Serverless features (2024-2026)

- **Cross-Region snapshot copy (2024-2025):** automated snapshot copy
  to a secondary Region for disaster recovery. Requires a separate
  destination-Region KMS key and a snapshot copy grant. RPO is the
  snapshot interval (default 8 hours).
- **Cost controls with usage thresholds (2024-2025):** usage limits
  with `breach-action` of `log`, `emit-metric`, or `disable`. Pair
  with CloudWatch alarms on `ServerlessComputeCapacity` for proactive
  budget alerts.
- **AWS Secrets Manager integration (2024-2025):** admin password
  stored and rotated in Secrets Manager via managed rotation Lambda.
  Removes the need for manual rotation scripts.
- **Zero-ETL integrations (2024-2026):** near-real-time replication
  from Aurora PostgreSQL, RDS for PostgreSQL, and DynamoDB into
  Redshift Serverless without COPY/UNLOAD pipelines. Configured at
  the source database, not the namespace.
- **Concurrent scaling (2024-2025):** auto-scaling beyond base RPU for
  bursty workloads. Billed separately; pair with usage limits.
- **Query editor v2 enhancements (2024-2025):** schema visualizer,
  query history, saved queries, and chart exports.
- **ML-driven workload management (2024-2025):** automatic WLM queue
  tuning based on query patterns. No manual queue configuration.
- **Row-level security (2024-2026):** policy-based row filtering
  without view rewriting. Useful for multi-tenant analytics.

## Workload matrix

| Workload | Base RPU | Public access | Enhanced VPC | Usage limit | Cross-Region snapshots |
|---|---|---|---|---|---|
| **BI dashboard** | 32-64 | Disabled | Enabled | Daily 200 RPU-hr | Optional |
| **Ad-hoc analytics** | 128 | Disabled | Enabled | Daily 500 RPU-hr | Yes |
| **Heavy ETL (nightly)** | 256 | Disabled | Enabled | Daily 1000 RPU-hr (peak at night) | Yes |
| **Multi-tenant SaaS** | 128-256 | Disabled | Enabled | Monthly 12000 RPU-hr | Yes |
| **Dev/test** | 8-32 | Disabled | Disabled | Monthly 500 RPU-hr | No |
| **Real-time (zero-ETL)** | 128 | Disabled | Enabled | Monthly 15000 RPU-hr | Yes |

## NEVER (top 5 — full list of 12 in references)

- NEVER create a namespace with the AWS-owned KMS key for production.
  The AWS-owned key cannot be audited, rotated, shared cross-account,
  or used for cross-Region snapshot copy. Migrating encryption keys
  after creation requires a full UNLOAD/LOAD cycle. #1 rollback-breaker.
- NEVER enable `publicly-accessible=true` on a production workgroup.
  A data warehouse should never be reachable from the public internet.
  Use a bastion, VPN, or Direct Connect for admin access.
- NEVER deploy a workgroup without `enhanced_vpc_routing=true` if you
  COPY/UNLOAD from/to S3. Without it, COPY/UNLOAD traffic traverses
  the public internet via Amazon S3 endpoints, which violates most
  compliance regimes (HIPAA, PCI, SOC2).
- NEVER set `breach-action=disable` on a production usage limit without
  a runbook. A threshold breach silently turns off ALL queries. Use
  `log` or `emit-metric` with a CloudWatch alarm for production.
- NEVER delete the cross-Region snapshot CMK while a snapshot copy
  grant references it. The next scheduled cross-Region copy will fail
  silently, and you will not know until a DR failover is attempted.

## Expert heuristic — sizing, cost controls, and snapshot strategy

- **RPU sizing:** start at 128 RPU for a moderate analytics workload
  (10-50 concurrent queries, 1-5 TB). For heavy ETL with nightly
  windowed loads, scale to 256+ RPU during the window and rely on
  concurrent scaling for daytime BI.
- **The 80/20 budget rule:** set the daily usage limit at 80% of your
  daily budget and the monthly limit at 120%. The daily limit catches
  runaway queries early; the monthly limit is the hard ceiling.
- **Snapshot interval vs cost:** every snapshot consumes storage at
  the source Region AND the destination Region. An 8-hour interval is
  a good default; a 1-hour interval doubles snapshot storage cost.
- **Data API vs JDBC:** use the Data API for Lambda, Step Functions,
  and EventBridge integrations (no connection pool needed). Use JDBC
  for BI tools that require persistent connections (Tableau, Looker).
- **CMK rotation:** enable annual KMS key rotation. Redshift Serverless
  handles re-encryption transparently.
- **Log exports:** set `userlog`, `connectionlog`, `useractivitylog`
  at namespace creation. CloudWatch log group is `/aws/redshift/<namespace>`.
  Retention defaults to Never Expire — set a retention policy.

## Pre-flight safety checks (run before any deployment CLI)

- **Confirm CMK exists and key policy allows `redshift-serverless`.**
- **Confirm subnet group spans 3+ AZs.**
- **Confirm security group inbound rule for port 5439 from analytics
  app SG.** NEVER `0.0.0.0/0`.
- **Confirm namespace IAM role trusts `redshift.amazonaws.com`.**
- **Confirm Secrets Manager secret exists (if used for admin password).**
- **Confirm service quota for RPU-hours is sufficient.**
- **For cross-Region snapshots, confirm destination-Region CMK exists.**
- **For existing namespaces, capture current config for rollback.**

Full CLI sequences for all checks in `references/configuration-and-cost-guide.md`.

## Output format — MANDATORY literal labels

When invoked with a Redshift Serverless deployment request, your
ENTIRE response MUST be the checklist block below. The labels are
**case-sensitive all-caps keywords**. Do NOT write a preamble. Start
with `WORKGROUP:` and stop after the `VERIFICATION_COMMANDS:` block.

```text
WORKGROUP: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Namespace — <namespace-name>, database <db-name>, admin user <admin>
  [✓]      Admin credentials — Secrets Manager secret <secret-arn> | manual password (rotate <days>)
  [✓]      KMS encryption — customer-managed key <key-arn> (encryption enabled) | AWS-owned (NOT recommended)
  [✓]      IAM roles — <namespace-role> (<data-plane-permissions>)
  [✓]      VPC security groups — <sg-ids> (inbound 5439 from <source-sg>)
  [✓]      Workgroup — <workgroup-name>, base capacity <rpu> RPU
  [✓]      Subnet group — <subnet-group> (<subnet-count> subnets across <az-count> AZs)
  [✓]      Public access — enabled | disabled
  [✓]      Enhanced VPC routing — enabled | disabled
  [✓]      Usage limits — daily <daily> RPU-hours, monthly <monthly> RPU-hour budget (<breach-action>)
  [✓]      Data API — enabled | disabled
  [✓]      Query editor v2 — associated (<iam-policy>)
  [✓]      Snapshots — automated every <interval>, <retention>-day retention, cross-Region copy to <dest-region> with KMS <dest-key-arn>
  [OPTIONAL] Concurrency scaling — enabled (auto-scaling beyond base RPU)
VERIFICATION_COMMANDS:
  aws redshift-serverless describe-workgroup --workgroup-name <wg>
  aws redshift-serverless describe-namespace --namespace-name <ns>
  aws redshift-serverless list-usage-limits
  aws secretsmanager describe-secret --secret-id <secret-id>
  aws kms describe-key --key-id <key-alias>
```

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required.
- `[INPUT NEEDED]` — prerequisite value missing; operator must provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (CMK for production, subnet group with 3+ AZs, security group
with port 5439 inbound, namespace IAM role for COPY/UNLOAD, Secrets
Manager secret for admin password), the verdict is
`PREREQUISITES_MISSING`.

## Domain

AWS CloudOps / Redshift Serverless Analytics Data Warehouse
Provisioning.

## Edge-case handling

- **Migrating from provisioned Redshift to Serverless:** use the
  `restore-from-cluster-snapshot` flow. The snapshot is restored into
  a new Serverless namespace. Database objects and data transfer;
  cluster parameter groups do NOT transfer (Serverless uses
  config-parameters on the workgroup).
- **Cross-account data sharing:** use datashares. The producer account
  creates a datashare; the consumer account creates a namespace and
  references the datashare. NEVER share the namespace IAM role across
  accounts.
- **Multi-AZ requirement:** Redshift Serverless is multi-AZ by default
  (subnet group must span 3+ AZs). There is no "single-AZ" mode.
- **Zero-ETL from Aurora:** configured at the Aurora cluster, not the
  Redshift namespace. The Aurora cluster needs a `redshift.amazonaws.com`
  role to push data. Replication lag is typically seconds.
- **Secrets Manager rotation:** the managed rotation Lambda runs every
  30 days by default. Override with a custom rotation schedule via
  Secrets Manager. The rotation updates BOTH the secret AND the
  namespace admin password atomically.
- **Usage limit reset:** when `breach-action=disable` triggers, the
  workgroup stays disabled until the next billing period OR until you
  manually delete the usage limit. NEVER use `disable` for production
  without an on-call runbook.
- **Cross-Region snapshot CMK deletion:** if you delete the
  destination-Region CMK, snapshot copies fail silently. CloudWatch
  metric `SnapshotCopyFailure` is the only signal. Set an alarm.

## AWS documentation

- **Redshift Serverless Developer Guide** — https://docs.aws.amazon.com/redshift/latest/dg/serverless-whatis.html
- **CreateNamespace API** — https://docs.aws.amazon.com/redshift-serverless/latest/APIReference/API_CreateNamespace.html
- **CreateWorkgroup API** — https://docs.aws.amazon.com/redshift-serverless/latest/APIReference/API_CreateWorkgroup.html
- **Redshift Serverless Usage Limits** — https://docs.aws.amazon.com/redshift/latest/dg/serverless-usage-limits.html
- **Redshift Data API** — https://docs.aws.amazon.com/redshift/latest/dg/data-api.html
- **Cross-Region Snapshots** — https://docs.aws.amazon.com/redshift/latest/dg/serverless-cross-region-snapshots.html
- **Query Editor v2** — https://docs.aws.amazon.com/redshift/latest/dg/query-editor-v2.html
- **Zero-ETL Integrations** — https://docs.aws.amazon.com/redshift/latest/dg/zero-etl.html
- **Redshift Serverless CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/redshift-serverless/

## References

- `references/cli-commands-and-iac.md` — full copy-pasteable CLI command
  sequence for all 11 deployment steps, including KMS key creation,
  subnet group creation, namespace IAM role, Secrets Manager secret,
  namespace creation, workgroup creation, usage limits, scheduled
  snapshots, cross-Region snapshot copy, and Terraform /
  CloudFormation equivalents.

- `references/configuration-and-cost-guide.md` — deep reference on
  encryption strategy, VPC networking, usage-limit tuning, snapshot
  and cross-Region DR strategy, Data API patterns, query editor v2
  setup, full NEVER list, edge-case handling, and pre-flight safety
  CLI.
