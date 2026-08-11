# Eval: s3-parquet-lambda-transform

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Direct PUT source, Lambda transformation, Parquet format conversion via Glue, S3 destination with Hive-style prefix, buffering hints tuned for Parquet (128MB)

## Prompt

Create a Firehose delivery stream named events-to-s3-parquet in
us-east-1, account 123456789012. Source: Direct PUT. Lambda
transformation using function
arn:aws:lambda:us-east-1:123456789012:function:firehose-transform
with buffer 3MB. Format conversion to Parquet using Glue database
analytics, table events_table. S3 destination bucket
my-data-lake with Hive-style prefix
data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/.
Error prefix
errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/.
Buffering hints 128MB / 300s. KMS encryption with key
arn:aws:kms:us-east-1:123456789012:key/abc123. Backup to
firehose-backup bucket. Tags: Environment=production,
Pipeline=events.
