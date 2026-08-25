# Kinesis Data Firehose Delivery Stream Auditor — error handling (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Remediation guidance — per-verdict fixes (moved from SKILL.md)

### For NO_ENCRYPTION — explicit NoEncryption

1. Identify why `NoEncryption` was set. Common causes: a Terraform
   module that omits the block, a legacy stream from before SSE-KMS
   support, or a deliberate choice for a non-sensitive workload.
2. If the workload is sensitive (PII, financial, healthcare), enable
   SSE-KMS with a customer-managed key:
   ```bash
   aws firehose update-destination \
     --delivery-stream-name <name> \
     --current-delivery-stream-version-id <version> \
     --destination-id destinationId-000000000001 \
     --extended-s3-update '{
       "EncryptionConfiguration": {
         "KMSEncryptionConfig": { "AWSKMSKeyArn": "arn:aws:kms:us-east-1:111111111111:key/abc-123" }
       }
     }'
   ```
3. If the workload is non-sensitive and SSE-S3 (AES256) is acceptable,
   REMOVE the explicit `NoEncryption` block so the stream inherits the
   bucket default declaratively:
   ```bash
   # Update with an EncryptionConfiguration block that uses bucket default
   # (Firehose will write with SSE-S3 unless the bucket enforces SSE-KMS)
   aws firehose update-destination ... --extended-s3-update '{"EncryptionConfiguration": {"NoEncryption": {}}}'
   # ^ This is the literal API — to REMOVE the explicit opt-out, omit
   # the block entirely in the update payload, or use a fresh destination config.
   ```
4. Verify the CMK policy grants Firehose before the update (see
   Pre-flight). Re-audit with this skill after `DeliveryStreamStatus`
   returns to ACTIVE.

### For CONFIG_GAP — absent EncryptionConfiguration (Step 1c)

1. Add an explicit `KMSEncryptionConfig` block referencing a same-region
   CMK (preferred), or document acceptance of bucket-default SSE-S3 in
   the workload's risk register.
2. Re-audit after the update — the block should appear under
   `ExtendedS3DestinationConfiguration.EncryptionConfiguration`.

### For CONFIG_GAP — BufferingHints out of range (Step 2)

1. Correct the values to within `[1,128]` MiB and `[60,900]` seconds.
2. For Parquet/ORC destinations, prefer `SizeInMBs: 128` to amortise
   row-group write cost; for JSON/CSV, prefer the 5 MiB default.
3. `aws firehose update-destination --extended-s3-update '{"BufferingHints": {"SizeInMBs": 64, "IntervalInSeconds": 300}}'`

### For CONFIG_GAP — Lambda transformation without source backup (Step 3)

1. Add `S3BackupConfiguration` to the ExtendedS3 destination with a
   dedicated backup bucket and prefix:
   ```bash
   aws firehose update-destination --extended-s3-update '{
     "S3BackupMode": "Enabled",
     "S3BackupConfiguration": {
       "RoleARN": "arn:aws:iam::111111111111:role/firehose-backup",
       "BucketARN": "arn:aws:s3:::firehose-backup-prod",
       "Prefix": "lambda-source/",
       "BufferingHints": {"SizeInMBs": 5, "IntervalInSeconds": 300}
     }
   }'
   ```
2. Verify the backup bucket's lifecycle policy — long-running
   transformation streams accumulate backup data indefinitely.

### For CONFIG_GAP — LoggingConfig disabled or absent (Step 4)

1. Enable on the stream (top-level config, not per-destination):
   ```bash
   aws firehose update-destination --delivery-stream-name <name> \
     --current-delivery-stream-version-id <version> \
     --destination-id destinationId-000000000001 \
     --extended-s3-update '{"...": "..."}'
   # LoggingConfig is a top-level field on certain CLI versions; on older
   # versions, recreate the stream. Verify with: aws firehose help update-destination
   ```
2. Set a retention period on the log group (`logs put-retention-policy`)
   — Firehose error volume can be high on misconfigured transformations.

### For CONFIG_GAP — DP without source backup (Step 5a)

1. Add `S3BackupConfiguration` (same guidance as Step 3). The backup
   captures the pre-partitioned raw record, which is the recovery
   source when JQ extraction fails.
2. Verify the JQ expression against representative records using
   `jq '<expr>'` locally before relying on it in production.

### For CONFIG_GAP — DP with RetryDuration: 0 (Step 5b)

1. Set `RetryDuration` to 300 (the max) for maximum resilience:
   ```bash
   aws firehose update-destination --extended-s3-update '{
     "DynamicPartitioningConfiguration": {"Enabled": true, "RetryDuration": 300}
   }'
   ```
2. Investigate WHY RetryDuration is 0 — it is not the default, which
   means an operator explicitly chose immediate-fail semantics.

### For OK

1. No remediation required.
2. Recommend verifying the CMK rotation status (refer to
   kms-key-policy-auditor) — encryption posture is only as strong as
   the key.
3. Recommend an `ErrorOutputPrefix` template if not set:
   `!{partitionKeyFromQuery:errorType}/!{timestamp:yyyy/MM/dd}/` —
   enables error triage without full log inspection.
4. Recommend `S3BackupMode: Enabled` (all data) over
   `FailedDataOnly` for streams where transformation correctness is
   load-bearing.
