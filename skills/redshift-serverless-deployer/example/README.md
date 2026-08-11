# End-to-End Example: Redshift Serverless Deployment

A walkthrough showing how to use the `redshift-serverless-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a production Redshift Serverless namespace and
workgroup for an analytics platform. The deployment requires:

- Customer-managed KMS encryption (CMK)
- Secrets Manager admin credential with auto-rotation
- Namespace IAM role for COPY/UNLOAD from S3
- 3-AZ subnet group with security group inbound on port 5439
- Base capacity 128 RPU
- Enhanced VPC routing (COPY/UNLOAD stays in VPC)
- Data API enabled for Lambda/Step Functions integrations
- Query editor v2 associated
- Usage limits: daily 500 RPU-hours (log), monthly 12000 RPU-hours (emit-metric)
- Log exports: userlog, connectionlog, useractivitylog
- Scheduled snapshots every 8 hours with 7-day retention
- Cross-Region snapshot copy to us-west-2 for DR

Namespace: `analytics-ns-prod`
Workgroup: `analytics-wg-prod`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-redshift-serverless
```

Then paste the namespace and workgroup requirements.

### Option B: Natural language

```
You: "Deploy a production Redshift Serverless namespace
      analytics-ns-prod and workgroup analytics-wg-prod in
      us-east-1. Database dev, admin user admin via Secrets
      Manager secret redshift/admin. Customer-managed KMS key
      alias/redshift-prod. Namespace IAM role RedshiftNSRole
      with S3 GetObject on ingest-bucket. Subnet group
      redshift-subnet-group across 3 AZs. Security group
      sg-redshift-prod with inbound 5439 from sg-analytics-app.
      Base capacity 128 RPU, public access disabled, enhanced
      VPC routing enabled, Data API enabled. Usage limits:
      daily 500 RPU-hours, monthly 12000 RPU-hours. Snapshots
      every 8 hours, 7-day retention, cross-Region copy to
      us-west-2. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy redshift serverless"
```

Output:

```
[Phase: Deploy | Skills routed: redshift-serverless-deployer]

Primary route: redshift-serverless-deployer (score: 18)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
WORKGROUP: analytics-wg-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Namespace — analytics-ns-prod, database dev, admin user admin
  [✓]      Admin credentials — Secrets Manager secret redshift/admin
  [✓]      KMS encryption — customer-managed key alias/redshift-prod (encryption enabled)
  [✓]      IAM roles — RedshiftNSRole (S3 GetObject on ingest-bucket, Glue GetTable)
  [✓]      VPC security groups — sg-redshift-prod (inbound 5439 from sg-analytics-app)
  [✓]      Workgroup — analytics-wg-prod, base capacity 128 RPU
  [✓]      Subnet group — redshift-subnet-group (3 subnets across 3 AZs)
  [✓]      Public access — disabled
  [✓]      Enhanced VPC routing — enabled
  [✓]      Usage limits — daily 500 RPU-hours (log), monthly 12000 RPU-hour budget (emit-metric)
  [✓]      Data API — enabled
  [✓]      Query editor v2 — associated
  [✓]      Log exports — userlog, connectionlog, useractivitylog
  [✓]      Snapshots — automated every 8 hours, 7-day retention, cross-Region copy to us-west-2 with KMS alias/redshift-dr
VERIFICATION_COMMANDS:
  aws redshift-serverless describe-workgroup --workgroup-name analytics-wg-prod
  aws redshift-serverless describe-namespace --namespace-name analytics-ns-prod
  aws redshift-serverless list-usage-limits
  aws redshift-serverless describe-scheduled-actions
  aws secretsmanager describe-secret --secret-id redshift/admin
  aws kms describe-key --key-id alias/redshift-prod
```

---

## Step 3 — Deployment commands

The skill generates the CLI sequence (from
`references/cli-commands-and-iac.md`):

```bash
# Step 1: KMS key (customer-managed, recommended for production)
aws kms create-key --description "Redshift Serverless production key" \
  --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"redshift-serverless.amazonaws.com"},"Action":["kms:Encrypt","kms:Decrypt","kms:ReEncrypt*","kms:GenerateDataKey*","kms:CreateGrant","kms:DescribeKey"],"Resource":"*"}]}'

aws kms create-alias --alias-name alias/redshift-prod \
  --target-key-id <key-id>

# Step 2: Subnet group
aws redshift-serverless create-subnet-group \
  --subnet-group-name redshift-subnet-group \
  --subnet-ids subnet-aaa subnet-bbb subnet-ccc \
  --security-group-ids sg-redshift-prod

# Step 3: Namespace IAM role
aws iam create-role \
  --role-name RedshiftNSRole \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"redshift.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

aws iam put-role-policy \
  --role-name RedshiftNSRole \
  --policy-name redshift-data-access \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:GetObject","s3:ListBucket"],"Resource":["arn:aws:s3:::ingest-bucket","arn:aws:s3:::ingest-bucket/*"]},{"Effect":"Allow","Action":["glue:GetTable","glue:GetDatabase","glue:GetPartitions"],"Resource":"*"}]}'

# Step 4: Secrets Manager admin credential
aws secretsmanager create-secret \
  --name redshift/admin \
  --secret-string '{"username":"admin","password":"<generated>","engine":"redshift","port":5439}'

# Step 5: Namespace
aws redshift-serverless create-namespace \
  --namespace-name analytics-ns-prod \
  --admin-username admin \
  --admin-user-password '<password-from-secrets>' \
  --db-name dev \
  --kms-key-id alias/redshift-prod \
  --default-iam-role-arn arn:aws:iam::123456789012:role/RedshiftNSRole \
  --iam-roles arn:aws:iam::123456789012:role/RedshiftNSRole \
  --security-group-ids sg-redshift-prod \
  --log-exports userlog connectionlog useractivitylog

# Step 6: Workgroup
aws redshift-serverless create-workgroup \
  --workgroup-name analytics-wg-prod \
  --namespace-name analytics-ns-prod \
  --base-capacity 128 \
  --subnet-group-name redshift-subnet-group \
  --security-group-ids sg-redshift-prod \
  --publicly-accessible false \
  --config-parameters '[{"parameterKey":"enable_data_api","parameterValue":"true"},{"parameterKey":"enhanced_vpc_routing","parameterValue":"true"},{"parameterKey":"require_ssl","parameterValue":"true"}]'

# Step 7: Usage limits
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

# Step 8: Scheduled snapshot + cross-Region copy
aws kms create-key --description "Redshift DR key in us-west-2" --region us-west-2
aws kms create-alias --alias-name alias/redshift-dr --target-key-id <dest-key-id> --region us-west-2
aws redshift create-snapshot-copy-grant --snapshot-copy-grant-name analytics-copy-grant --kms-key-id alias/redshift-dr --region us-west-2

aws redshift-serverless create-scheduled-action \
  --scheduled-action-name analytics-snapshot-schedule \
  --namespace-name analytics-ns-prod \
  --schedule "rate(8 hours)" \
  --target-action '{"CreateSnapshot":{"NamespaceName":"analytics-ns-prod","SnapshotName":"analytics-snapshot"}}'

aws redshift-serverless update-namespace \
  --namespace-name analytics-ns-prod \
  --snapshot-copy-configurations '[{"DestinationRegion":"us-west-2","SnapshotCopyGrantName":"analytics-copy-grant","RetentionPeriod":7}]'
```

---

## Step 4 — Post-deployment verification

```bash
# Workgroup status and config
aws redshift-serverless describe-workgroup \
  --workgroup-name analytics-wg-prod

# Namespace status and encryption
aws redshift-serverless describe-namespace \
  --namespace-name analytics-ns-prod

# Usage limits
aws redshift-serverless list-usage-limits

# Scheduled snapshot actions
aws redshift-serverless describe-scheduled-actions

# Secrets Manager secret
aws secretsmanager describe-secret \
  --secret-id redshift/admin

# KMS keys (source + destination)
aws kms describe-key --key-id alias/redshift-prod
aws kms describe-key --key-id alias/redshift-dr --region us-west-2

# Log groups
aws logs describe-log-groups \
  --log-group-name-prefix /aws/redshift/analytics-ns-prod

# Data API test query
aws redshift-data execute-statement \
  --workgroup-name analytics-wg-prod \
  --database dev \
  --secret-arn arn:aws:secretsmanager:us-east-1:123456789012:secret:redshift/admin-XXX \
  --sql "SELECT current_database(), current_user"
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| KMS encryption | AWS-owned default key | Customer-managed CMK with rotation | AWS-owned key cannot be audited, rotated, or used for cross-Region snapshots. Migration requires full UNLOAD/LOAD. |
| Admin credentials | Hardcoded password | Secrets Manager with auto-rotation | Hardcoded passwords expire; Secrets Manager rotates atomically. |
| Enhanced VPC routing | Not enabled | Enabled | Without it, COPY/UNLOAD traverses the public internet, violating compliance. |
| Usage limits | Not set | Daily + monthly limits with CloudWatch alarm | A runaway query can exhaust the budget in hours. |
| Security group inbound | Often `0.0.0.0/0` or missing | Port 5439 from analytics app SG only | A data warehouse should never be reachable from the public internet. |
| Cross-Region snapshots | Not configured | Scheduled copy with separate destination-Region CMK | DR requires a separate Region CMK; reusing the source key fails. |
| Log exports | Not set at creation | userlog, connectionlog, useractivitylog | Log exports are NOT retroactive — set at namespace creation. |

---

## Related artifacts

- **Skill definition:** `skills/redshift-serverless-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/redshift-serverless-deployer/references/cli-commands-and-iac.md`
- **Configuration and cost guide:** `skills/redshift-serverless-deployer/references/configuration-and-cost-guide.md`
- **Slash command:** `commands/aws/deploy-redshift-serverless.md`
- **Eval suite:** `skills/redshift-serverless-deployer/evals/evals.json`
- **Legacy test cases:** `skills/redshift-serverless-deployer/eval/test-cases.yaml`
