# End-to-End Example: Firehose Delivery Stream Deployment

A walkthrough showing how to use the `firehose-delivery-stream-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Firehose delivery stream that ingests events via
Direct PUT, transforms them with Lambda, converts to Parquet using a
Glue schema, and delivers to an S3 data lake with Hive-style
partitioning. The stream needs:

- Stream name: events-to-s3-parquet
- Source: Direct PUT
- Lambda transformation: firehose-transform function (buffer 3MB)
- Format conversion: Parquet (Glue analytics/events_table)
- S3 destination: my-data-lake bucket
- S3 prefix: Hive-style (year/month/day)
- Buffering hints: 128MB / 300s (tuned for Parquet)
- KMS encryption: customer-managed key
- Backup: FailedDocumentsOnly to firehose-backup

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-firehose-delivery-stream
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Firehose delivery stream named events-to-s3-parquet.
      Direct PUT source. Lambda transform with 3MB buffer. Convert
      to Parquet using Glue analytics/events_table. S3 bucket
      my-data-lake with Hive-style prefix. Buffering 128MB."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a firehose delivery stream"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
FIREHOSE: events-to-s3-parquet (Direct PUT → S3)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Source: Direct PUT
  [✓] Lambda transformation: enabled (arn:aws:lambda:us-east-1:123456789012:function:firehose-transform, buffer 3MB)
  [✓] Format conversion: Parquet (Glue analytics/events_table)
  [✓] Destination: S3 (arn:aws:s3:::my-data-lake, prefix data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/)
  [✓] Buffering hints: 128MB / 300s (tuned for Parquet — optimal row group size)
  [✓] S3 prefix: Hive-style partitioned (year/month/day)
  [✓] Error prefix: errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/
  [✓] Compression: UNCOMPRESSED (Parquet has built-in compression)
  [✓] Backup: FailedDocumentsOnly → arn:aws:s3:::firehose-backup
  [✓] Retry: 300s
  [✓] CloudWatch logging: enabled
  [✓] KMS encryption: enabled (arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] IAM role: arn:aws:iam::123456789012:role/FirehoseStreamRole (trust: firehose.amazonaws.com)
  [✓] Tags: Environment=production, Pipeline=events
VERIFICATION_COMMANDS:
  aws firehose describe-delivery-stream --delivery-stream-name events-to-s3-parquet --region us-east-1
  aws firehose describe-delivery-stream --delivery-stream-name events-to-s3-parquet --query 'DeliveryStreamDescription.DeliveryStreamStatus' --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the IAM role (trust firehose.amazonaws.com)
aws iam create-role \
  --role-name FirehoseStreamRole \
  --assume-role-policy-document file://trust-policy.json

# Step 2: Attach permissions (S3, Lambda, Glue, KMS, Logs)
aws iam put-role-policy \
  --role-name FirehoseStreamRole \
  --policy-name FirehosePermissions \
  --policy-document file://permissions.json

# Step 3: Create the delivery stream
aws firehose create-delivery-stream \
  --delivery-stream-name events-to-s3-parquet \
  --delivery-stream-type DirectPut \
  --extended-s3-destination-configuration '{
    "RoleARN": "arn:aws:iam::123456789012:role/FirehoseStreamRole",
    "BucketARN": "arn:aws:s3:::my-data-lake",
    "Prefix": "data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/",
    "ErrorOutputPrefix": "errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/",
    "BufferingHints": {"SizeInMBs": 128, "IntervalInSeconds": 300},
    "CompressionFormat": "UNCOMPRESSED",
    "EncryptionConfiguration": {
      "KMSEncryptionConfig": {"AWSKMSKeyARN": "arn:aws:kms:us-east-1:123456789012:key/abc123"}
    },
    "ProcessingConfiguration": {
      "Enabled": true,
      "Processors": [{
        "Type": "Lambda",
        "Parameters": [
          {"ParameterName": "LambdaArn", "ParameterValue": "arn:aws:lambda:us-east-1:123456789012:function:firehose-transform"},
          {"ParameterName": "BufferSizeInMBs", "ParameterValue": "3"}
        ]
      }]
    },
    "DataFormatConversionConfiguration": {
      "Enabled": true,
      "InputFormatConfiguration": {"Deserializer": {"OpenXJsonSerDe": {}}},
      "OutputFormatConfiguration": {"Serializer": {"ParquetSerDe": {}}},
      "SchemaConfiguration": {
        "DatabaseName": "analytics",
        "TableName": "events_table",
        "RoleARN": "arn:aws:iam::123456789012:role/FirehoseStreamRole",
        "Region": "us-east-1"
      }
    },
    "S3BackupMode": "FailedDataOnly",
    "S3BackupConfiguration": {
      "RoleARN": "arn:aws:iam::123456789012:role/FirehoseStreamRole",
      "BucketARN": "arn:aws:s3:::firehose-backup",
      "Prefix": "failed/"
    }
  }' --region us-east-1

# Step 4: Wait for the stream to become ACTIVE
aws firehose describe-delivery-stream \
  --delivery-stream-name events-to-s3-parquet \
  --query 'DeliveryStreamDescription.DeliveryStreamStatus' \
  --region us-east-1 --output text
# Wait until output is "ACTIVE"
```

---

## Step 4 — Post-deployment verification

```bash
# Stream status — should be ACTIVE
aws firehose describe-delivery-stream \
  --delivery-stream-name events-to-s3-parquet \
  --query 'DeliveryStreamDescription.DeliveryStreamStatus' \
  --region us-east-1

# Verify destination configuration
aws firehose describe-delivery-stream \
  --delivery-stream-name events-to-s3-parquet \
  --query 'DeliveryStreamDescription.Destinations[0].ExtendedS3DestinationDescription.{Buffering:BufferingHints,Prefix:Prefix,Conversion:DataFormatConversionConfiguration.Enabled}' \
  --region us-east-1 --output table

# Test data ingestion (Direct PUT)
aws firehose put-record \
  --delivery-stream-name events-to-s3-parquet \
  --record '{"Data":"eyJldmVudCI6ICJ0ZXN0IiwgInVzZXIiOiAiYWxpY2UifQ=="}' \
  --region us-east-1

# Verify S3 objects (wait 5+ minutes for buffering flush)
aws s3 ls s3://my-data-lake/data/year=2026/month=01/day=15/ --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Buffering hints | Default 5MB | 128MB for Parquet | Tiny Parquet files degrade Athena performance; 64+ MB produces optimal row groups |
| S3 prefix | Flat prefix | Hive-style partitioned | Flat prefix means Athena scans all files; Hive-style enables partition pruning |
| Compression + Parquet | GZIP (double-compression) | UNCOMPRESSED | Parquet has built-in compression; GZIP wastes CPU |
| Backup | No backup | FailedDocumentsOnly to separate bucket | Without backup, failed records are lost |
| Glue permissions | Missing glue:GetTable | IAM role includes Glue permissions | Format conversion needs Glue table schema access |
| Lambda + conversion order | Not considered | Lambda output validated against Glue schema | Lambda runs before conversion; malformed JSON causes conversion failure |

---

## Related artifacts

- **Skill definition:** `skills/firehose-delivery-stream-deployer/SKILL.md`
- **Destinations and buffering guide:** `skills/firehose-delivery-stream-deployer/references/destinations-and-buffering.md`
- **Transformation and encryption guide:** `skills/firehose-delivery-stream-deployer/references/transformation-and-encryption.md`
- **Slash command:** `commands/aws/deploy-firehose-delivery-stream.md`
- **Eval suite:** `skills/firehose-delivery-stream-deployer/evals/evals.json`
- **Legacy test cases:** `skills/firehose-delivery-stream-deployer/eval/test-cases.yaml`
