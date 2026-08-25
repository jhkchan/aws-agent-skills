# Error Handling — Firehose Delivery Stream Deployer

Failure-mode deep dives, moved verbatim from SKILL.md § Error handling. Load on demand.

## Error handling
### Records going to error prefix with format conversion
- Lambda transformation outputting invalid JSON that does not match
  the Glue table schema. Verify the Lambda function returns valid JSON
  with fields matching the Glue table columns.

### Many tiny S3 files (high cost, slow Athena)
- Buffering hints too low for Parquet. Increase SizeInMBs to 64-128 MB
  for Parquet destinations to produce fewer, larger files.

### OpenSearch delivery falling behind
- Buffering hints too high for OpenSearch. Decrease to 5 MB and
  IntervalInSeconds to 60-300s. Also check OpenSearch cluster health.

### Firehose stream stuck in CREATING
- IAM role missing permissions for destination, Glue, or KMS. Verify
  the role trust policy and all required permissions.

### CloudWatch Logs subscription not delivering
- Subscription filter IAM role missing
  `firehose:PutRecordBatch` permission, or the Firehose stream not in
  ACTIVE state.
