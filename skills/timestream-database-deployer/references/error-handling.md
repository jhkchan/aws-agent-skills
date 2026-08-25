# Error Handling — Timestream Database Deployer

Failure deep dives moved verbatim from SKILL.md. Loaded on demand.

## Error handling

### Table creation fails — database not found
- The database must exist before creating a table. Verify with
  `describe-database`. Create the database first.

### Magnetic store write property update fails
- The S3 bucket must exist and have a bucket policy granting
  `s3:PutObject` to the Timestream service principal. Verify the
  bucket policy with `get-bucket-policy`. Ensure the bucket is in the
  same region as the table.

### Scheduled query execution fails
- Check the SNS notification for error details. Common causes: target
  table does not exist, IAM role lacks permissions, query syntax error,
  schema mismatch in dimension mappings. Verify the execution role has
  query, write, and SNS publish permissions.

### Batch load task stuck in PENDING
- Check IAM permissions for the batch load role. Verify the S3 data
  source bucket exists and contains data in the expected format (CSV
  with headers or Parquet).

### Late-arrival data silently rejected
- Magnetic store writes are disabled by default. Enable
  MagneticStoreWriteProperties with an S3 bucket destination. Verify
  the bucket policy grants Timestream write access.

### Memory store costs unexpectedly high
- Check the memory store TTL. A high TTL on a high-ingestion table
  retains a large volume of data in memory. Reduce the TTL or use
  scheduled queries to pre-compute aggregates with a shorter source
  TTL.
