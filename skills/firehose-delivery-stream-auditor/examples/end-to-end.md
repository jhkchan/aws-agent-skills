# End-to-end usage scenario: firehose-delivery-stream-auditor

A walkthrough showing the skill auditing a Kinesis Data Firehose
delivery stream that fails the encryption dimension (explicit
`NoEncryption`) and then a second stream that fails multiple
configuration dimensions (DP without source backup, LoggingConfig
disabled, buffering out of range). Demonstrates first-fail-wins
ordering, the NO_ENCRYPTION short-circuit, and the CLI remediation
workflow.

## Scenario 1: NO_ENCRYPTION (explicit opt-out)

### Input (user prompt)

> Audit this Firehose delivery stream. We onboarded it from an
> acquisition and I'm not sure about the encryption posture.

```json
{
  "DeliveryStreamName": "events-stream-legacy",
  "DeliveryStreamARN": "arn:aws:firehose:us-east-1:111111111111:deliverystream/events-stream-legacy",
  "DeliveryStreamStatus": "ACTIVE",
  "DeliveryStreamType": "DirectPut",
  "LoggingConfig": {"Enabled": true, "LogGroupName": "/aws/kinesisfirehose/events-stream-legacy"},
  "DeliveryStreamConfiguration": {
    "ExtendedS3DestinationConfiguration": {
      "RoleARN": "arn:aws:iam::111111111111:role/firehose-legacy",
      "BucketARN": "arn:aws:s3:::acquired-company-events",
      "Prefix": "ingest/",
      "BufferingHints": {"SizeInMBs": 15, "IntervalInSeconds": 300},
      "CompressionFormat": "GZIP",
      "EncryptionConfiguration": {"NoEncryption": {}},
      "S3BackupMode": "Disabled"
    }
  }
}
```

### Skill output

```text
STREAM: events-stream-legacy
VERDICT: NO_ENCRYPTION
REASON: EncryptionConfiguration.NoEncryption is explicitly set on the
ExtendedS3 destination — this is the only API path to plaintext Firehose
delivery and is always a deliberate operator choice (Step 1a). Short-
circuits all other dimensions.
FINDINGS:
  - [CRITICAL] Explicit NoEncryption on ExtendedS3DestinationConfiguration
    (Step 1a) — records are written to S3 in plaintext, modulo bucket
    policy enforcement. If the bucket does not enforce SSE, this is full
    plaintext at rest.
REMEDIATION:
  1. Determine whether the NoEncryption setting was intentional (legacy
     Terraform module, acquired infra) or a bug.
  2. If sensitive data flows through this stream, add a customer-managed
     KMS key:
     aws firehose update-destination \
       --delivery-stream-name events-stream-legacy \
       --current-delivery-stream-version-id <version> \
       --destination-id destinationId-000000000001 \
       --extended-s3-update '{"EncryptionConfiguration": {"KMSEncryptionConfig": {"AWSKMSKeyArn": "arn:aws:kms:us-east-1:111111111111:key/cmk-firehose-prod"}}}'
  3. Verify the CMK policy grants firehose.amazonaws.com
     kms:GenerateDataKey + kms:Decrypt BEFORE the update.
  4. Re-audit after DeliveryStreamStatus returns to ACTIVE.
```

## Scenario 2: CONFIG_GAP (DP without source backup, multiple findings)

### Input (user prompt)

> Audit this stream. We added dynamic partitioning last quarter and
> I want to make sure we're not flying blind.

```json
{
  "DeliveryStreamName": "clickstream-partitioned",
  "DeliveryStreamARN": "arn:aws:firehose:us-east-1:111111111111:deliverystream/clickstream-partitioned",
  "DeliveryStreamStatus": "ACTIVE",
  "DeliveryStreamType": "DirectPut",
  "LoggingConfig": {"Enabled": false, "LogGroupName": "/aws/kinesisfirehose/clickstream-partitioned"},
  "DeliveryStreamConfiguration": {
    "ExtendedS3DestinationConfiguration": {
      "RoleARN": "arn:aws:iam::111111111111:role/firehose-role",
      "BucketARN": "arn:aws:s3:::clickstream-prod",
      "Prefix": "year=!{partitionKeyFromQuery:year}/month=!{partitionKeyFromQuery:month}/",
      "BufferingHints": {"SizeInMBs": 64, "IntervalInSeconds": 300},
      "CompressionFormat": "SNAPPY",
      "EncryptionConfiguration": {
        "KMSEncryptionConfig": {"AWSKMSKeyArn": "arn:aws:kms:us-east-1:111111111111:key/cmk-firehose-prod"}
      },
      "S3BackupMode": "Disabled",
      "DynamicPartitioningConfiguration": {"Enabled": true, "RetryDuration": 0},
      "ProcessingConfiguration": {
        "Enabled": true,
        "Processors": [
          {
            "Type": "MetadataExtraction",
            "Parameters": [
              {"ParameterName": "JsonParsingEngine", "ParameterValue": "JQ-1.6"},
              {"ParameterName": "MetaDataExtractionQuery", "ParameterValue": "{year: .ts[0:4], month: .ts[5:7]}"}
            ]
          }
        ]
      }
    }
  }
}
```

### Skill output

```text
STREAM: clickstream-partitioned
VERDICT: CONFIG_GAP
REASON: Dynamic partitioning is enabled but S3BackupConfiguration is
absent — any JQ extraction failure causes silent record loss (Step 5a).
RetryDuration: 0 compounds the risk (Step 5b). LoggingConfig is also
disabled, so the failures would be invisible (Step 4). Encryption (Step
1) and buffering (Step 2) pass — all findings are configuration gaps.
FINDINGS:
  - [HIGH] DP enabled with no S3BackupConfiguration — silent data-loss
    vector on JQ extraction failure (Step 5a)
  - [HIGH] LoggingConfig.Enabled: false with ProcessingConfiguration
    enabled — transformation errors are invisible (Step 4)
  - [MEDIUM] DynamicPartitioningConfiguration.RetryDuration: 0 — single
    extraction failure is immediately fatal, no retry (Step 5b)
REMEDIATION:
  1. Add S3BackupConfiguration to capture pre-partitioned source records:
     aws firehose update-destination \
       --delivery-stream-name clickstream-partitioned \
       --current-delivery-stream-version-id <version> \
       --destination-id destinationId-000000000001 \
       --extended-s3-update '{
         "S3BackupMode": "Enabled",
         "S3BackupConfiguration": {
           "RoleARN": "arn:aws:iam::111111111111:role/firehose-role",
           "BucketARN": "arn:aws:s3:::clickstream-backup-prod",
           "Prefix": "dp-source/",
           "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 300},
           "EncryptionConfiguration": {"KMSEncryptionConfig": {"AWSKMSKeyArn": "arn:aws:kms:us-east-1:111111111111:key/cmk-firehose-prod"}}
         }
       }'
  2. Enable CloudWatch error logging (LoggingConfig is top-level):
     update via update-destination with the LoggingConfig field, or
     recreate the stream if your CLI version does not support top-level
     update. Verify with aws firehose describe-delivery-stream.
  3. Set RetryDuration to 300 (max) for maximum resilience:
     --extended-s3-update '{"DynamicPartitioningConfiguration": {"Enabled": true, "RetryDuration": 300}}'
  4. Capture current config before any update (update-destination is
     not reversible):
     aws firehose describe-delivery-stream --delivery-stream-name clickstream-partitioned --output json > /tmp/clickstream-partitioned-backup-$(date +%s).json
```

## Scenario 3: OK (clean posture)

A stream with CMK encryption, valid buffering, Lambda transformation
with source backup enabled, LoggingConfig enabled, dynamic partitioning
with source backup and RetryDuration 300. All dimensions pass — verdict
OK. See `evals/prompts/ok-cmk-lambda-dp-backup.md` for the canonical
clean input.
