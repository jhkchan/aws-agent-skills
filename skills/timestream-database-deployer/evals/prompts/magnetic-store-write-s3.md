# Eval: magnetic-store-write-s3

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — magnetic store write properties enabled, S3 bucket with bucket policy for late-arrival data

## Prompt

Create a Timestream database named IoTSensorData and table
EventLogs in us-east-1. Memory store TTL 6 hours, magnetic store
TTL 730 days. Enable magnetic store writes with S3 bucket
timestream-late-arrival-us-east-1 for late-arrival data. The
bucket already has a policy granting Timestream s3:PutObject.
Tags: Environment=production.
