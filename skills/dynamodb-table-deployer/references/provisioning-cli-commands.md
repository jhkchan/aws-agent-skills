# Provisioning CLI Commands — DynamoDB Table Deployer

Full copy-pasteable CLI command sequence for all 10 provisioning steps.
Variables to substitute: `<table>`, `<region>`, `<account-id>`, KMS key
ARNs, attribute names, capacity values, replica regions.

## Step 0: Prerequisites check

```bash
# Confirm caller identity
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm region
REGION=$(aws configure get region)
echo "Region: $REGION"

# Confirm table name is available (should return ResourceNotFoundException)
aws dynamodb describe-table --table-name <table> 2>&1 | head -3

# Confirm CMK exists and is enabled (if SSE-KMS customer CMK)
aws kms describe-key --key-id alias/<alias-name> --query 'KeyMetadata.[KeyId,KeyState,Enabled]' --output text

# Confirm CMK key policy grants DynamoDB
aws kms get-key-policy --key-id alias/<alias-name> --policy-name default --output text
```

## Step 1: Create the table with key schema + LSI + GSI + capacity + SSE-KMS

Single-shot create with all immutable properties (key schema, LSI, billing
mode, SSE). GSIs CAN be added post-creation but provisioning them at
create-time is preferred.

### On-demand mode + customer CMK + LSI + GSI

```bash
aws dynamodb create-table \
  --table-name <table> \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
    AttributeName=lsiSort,AttributeType=S \
    AttributeName=gsiPk,AttributeType=S \
    AttributeName=gsiSk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --local-secondary-indexes '[{
    "IndexName": "lsi_by_lsiSort",
    "KeySchema": [
      {"AttributeName":"pk","KeyType":"HASH"},
      {"AttributeName":"lsiSort","KeyType":"RANGE"}
    ],
    "Projection":{"ProjectionType":"ALL"}
  }]' \
  --global-secondary-indexes '[{
    "IndexName": "gsi_by_gsiPk",
    "KeySchema": [
      {"AttributeName":"gsiPk","KeyType":"HASH"},
      {"AttributeName":"gsiSk","KeyType":"RANGE"}
    ],
    "Projection":{"ProjectionType":"KEYS_ONLY"}
  }]' \
  --billing-mode PAY_PER_REQUEST \
  --table-class STANDARD \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=arn:aws:kms:<region>:<account-id>:alias/<alias-name> \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --deletion-protection-enabled
```

### Provisioned mode with autoscaling + customer CMK

```bash
aws dynamodb create-table \
  --table-name <table> \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --table-class STANDARD \
  --sse-specification Enabled=true,SSEType=KMS,KMSMasterKeyId=arn:aws:kms:<region>:<account-id>:alias/<alias-name> \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
  --deletion-protection-enabled
```

## Step 2: Register autoscaling (PROVISIONED mode only)

For each GSI in PROVISIONED mode, repeat with
`--resource-id table/<table>/index/<gsi-name>` and the
`dynamodb:index:*CapacityUnits` scalable dimensions.

```bash
# Table read
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/<table> \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 --max-capacity 40000

aws application-autoscaling put-scaling-policy \
  --policy-name <table>-read-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/<table> \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":60}'

# Table write
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/<table> \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 5 --max-capacity 40000

aws application-autoscaling put-scaling-policy \
  --policy-name <table>-write-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/<table> \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBWriteCapacityUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":60}'

# GSI read (repeat per GSI)
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/<table>/index/<gsi-name> \
  --scalable-dimension dynamodb:index:ReadCapacityUnits \
  --min-capacity 5 --max-capacity 10000

aws application-autoscaling put-scaling-policy \
  --policy-name <table>-<gsi-name>-read-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/<table>/index/<gsi-name> \
  --scalable-dimension dynamodb:index:ReadCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"}}'
```

## Step 3: Enable PITR

```bash
aws dynamodb update-continuous-backups \
  --table-name <table> \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

## Step 4: Enable TTL

```bash
aws dynamodb update-time-to-live \
  --table-name <table> \
  --time-to-live-specification Enabled=true,AttributeName=ttl
```

## Step 5: Add a GSI to an existing table (post-creation)

```bash
aws dynamodb update-table \
  --table-name <table> \
  --attribute-definitions AttributeName=gsiPk,AttributeType=S \
  --global-secondary-index-updates '[{
    "Create":{
      "IndexName":"gsi_by_gsiPk",
      "KeySchema":[{"AttributeName":"gsiPk","KeyType":"HASH"}],
      "Projection":{"ProjectionType":"KEYS_ONLY"},
      "ProvisionedThroughput":{"ReadCapacityUnits":5,"WriteCapacityUnits":5}
    }
  }]'
```

## Step 6: Resource-based policy (cross-account access)

```bash
aws dynamodb put-resource-policy \
  --resource-arn arn:aws:dynamodb:<region>:<account-id>:table/<table> \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::<dest-account-id>:root"},
      "Action": ["dynamodb:GetItem","dynamodb:BatchGetItem","dynamodb:Query"],
      "Resource": "arn:aws:dynamodb:<region>:<account-id>:table/<table>"
    }]
  }'
```

## Step 7: Global Tables v2 — add replicas

```bash
aws dynamodb create-global-table \
  --global-table-name <table> \
  --replication-group \
    RegionName=<primary-region>,RegionName=<replica-region>

# To add another replica later:
aws dynamodb update-global-table \
  --global-table-name <table> \
  --replica-updates '[{"Create":{"RegionName":"<new-replica-region>"}}]'
```

**Pre-check**: confirm the CMK exists in every replica region:

```bash
for r in us-east-1 us-west-2 eu-west-1; do
  aws kms describe-key --key-id alias/<alias-name> --region "$r" \
    --query 'KeyMetadata.[KeyId,KeyState]' --output text || \
  echo "MISSING CMK in $r — provision before adding replica"
done
```

## Step 8: CloudWatch alarms (recommended)

```bash
# Throttle alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "<table>-throttles" \
  --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> \
  --statistic Sum --period 60 --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 --alarm-actions <sns-arn>

# GSI throttle alarm (repeat per GSI)
aws cloudwatch put-metric-alarm \
  --alarm-name "<table>-<gsi>-throttles" \
  --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> Name=IndexName,Value=<gsi-name> \
  --statistic Sum --period 60 --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 --alarm-actions <sns-arn>

# SystemErrors
aws cloudwatch put-metric-alarm \
  --alarm-name "<table>-system-errors" \
  --namespace AWS/DynamoDB \
  --metric-name SystemErrors \
  --dimensions Name=TableName,Value=<table> \
  --statistic Sum --period 60 --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 --alarm-actions <sns-arn>

# Replication latency (Global Tables)
aws cloudwatch put-metric-alarm \
  --alarm-name "<table>-replication-latency" \
  --namespace AWS/DynamoDB \
  --metric-name ReplicationLatency \
  --dimensions Name=TableName,Value=<table> Name=ReceivingRegion,Value=<replica-region> \
  --statistic Average --period 60 --threshold 1000 \
  --comparison-operator GreaterThan --evaluation-periods 3 \
  --alarm-actions <sns-arn>
```

## Verification

```bash
aws dynamodb describe-table --table-name <table>
aws dynamodb describe-continuous-backups --table-name <table>
aws dynamodb describe-time-to-live --table-name <table>
aws dynamodb describe-kinesis-destination --table-name <table>
aws application-autoscaling describe-scaling-policies --service-namespace dynamodb --resource-id table/<table>
aws application-autoscaling describe-scaling-policies --service-namespace dynamodb --resource-id table/<table>/index/<gsi-name>
aws dynamodb get-resource-policy --resource-arn arn:aws:dynamodb:<region>:<account-id>:table/<table>
aws dynamodb describe-global-table --global-table-name <table>
aws kms describe-key --key-id alias/<alias-name>
```

## Terraform equivalent (aws_dynamodb_table + associated resources)

```hcl
resource "aws_dynamodb_table" "table" {
  name           = "<table>"
  billing_mode   = "PAY_PER_REQUEST"
  table_class    = "STANDARD"
  hash_key       = "pk"
  range_key      = "sk"
  stream_enabled = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  deletion_protection_enabled = true

  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
  attribute {
    name = "gsiPk"
    type = "S"
  }

  global_secondary_index {
    name            = "gsi_by_gsiPk"
    hash_key        = "gsiPk"
    projection_type = "KEYS_ONLY"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.dynamodb.arn
  }

  point_in_time_recovery {
    enabled = true
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Environment = "production"
    Workload    = "session-store"
  }
}

resource "aws_kms_key" "dynamodb" {
  description             = "Customer CMK for DynamoDB table <table>"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "Enable IAM User Permissions"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::<account-id>:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "Allow DynamoDB Service"
        Effect    = "Allow"
        Principal = { Service = "dynamodb.<region>.amazonaws.com" }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
}
```

---

## Step 5 PROVISIONED autoscaling registration CLI (moved from SKILL.md)

**PROVISIONED autoscaling registration (MANDATORY if PROVISIONED)**:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/<table> \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 --max-capacity <max>
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/<table> \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 5 --max-capacity <max>

aws application-autoscaling put-scaling-policy \
  --policy-name <table>-read-autoscaling \
  --service-namespace dynamodb \
  --resource-id table/<table> \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"}}'
# Repeat for WriteCapacityUnits and for EVERY GSI:
#   --resource-id table/<table>/index/<gsi-name>
#   --scalable-dimension dynamodb:index:ReadCapacityUnits (and Write)
```

---

## Step 7 — Point-in-time recovery (PITR) — enable by default (moved from SKILL.md)

Enable PITR on every production table. PITR provides a 35-day continuous
replay window — restore to any second within the window. AWS Backup
(scheduled snapshots) is COMPLEMENTARY, not a substitute.

```bash
aws dynamodb update-continuous-backups --table-name <table> \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

**PITR restore creates a NEW table** — it cannot rewind the original. The
restored table gets DEFAULT capacity settings; reconfigure after restore.

**Cost note**: PITR consumes additional storage proportional to the change
rate. For most production tables the recovery benefit outweighs the cost.

---

## Step 9 — Streams + table class + deletion protection (moved from SKILL.md)

Three additive, reversible configurations:

**DynamoDB Streams** (for CDC pipelines — Lambda triggers, OpenSearch
sync, Kinesis replay, Aurora zero-ETL):

```bash
aws dynamodb update-table --table-name <table> \
  --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES
```

Choose `StreamViewType` based on the consumer:
- `NEW_IMAGE` — consumer needs only the post-update state (e.g., search index sync).
- `OLD_IMAGE` — consumer needs only the pre-update state (e.g., audit log of deletions).
- `NEW_AND_OLD_IMAGES` — consumer needs both (e.g., diff-based replication, Aurora zero-ETL, full CDC).
- `KEYS_ONLY` — consumer needs only the keys (e.g., trigger a Lambda to re-fetch).

Streams have a 24-hour retention window. For longer retention, fan out to
Kinesis Data Streams.

**Table class** (`STANDARD` vs `STANDARD_INFREQUENT_ACCESS`):

```bash
aws dynamodb update-table --table-name <table> --table-class STANDARD_INFREQUENT_ACCESS
```

- `STANDARD` (default): for actively-used tables.
- `STANDARD_INFREQUENT_ACCESS`: for cold / infrequently accessed tables
  (audit logs, archives). Lower storage cost; higher per-request cost.
  Use only when access is rare.

**Deletion protection** (blocks `delete-table` API):

```bash
aws dynamodb update-table --table-name <table> --deletion-protection-enabled
```

Mandatory for production tables. Blocks accidental deletion and ransomware.
Note: any principal with `dynamodb:UpdateTable` can disable it — it is an
accidental-deletion guardrail, not a security control.
