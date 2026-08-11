# Eval: s3-target-parquet-format

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — S3 target with Parquet DataFormat, Snappy CompressionType, RLE dictionary encoding, column names included

## Prompt

Create a DMS target endpoint for S3 in us-east-1. Bucket
my-dms-target-bucket, folder /migration-data/. Data format
Parquet with Snappy compression and RLE dictionary encoding.
Include column names in output. Service access role
arn:aws:iam::123456789012:role/dms-s3-role. KMS key
arn:aws:kms:us-east-1:123456789012:key/s3-key. Replication
instance rep-instance-prod. Tags: Environment=production,
Format=parquet.
