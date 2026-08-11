# Eval: missing-s3-bucket-policy

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — S3 bucket lacks bucket policy granting Timestream s3:PutObject; magnetic store writes will silently fail

## Prompt

Create a Timestream table LateArrivalData with magnetic store
writes enabled using S3 bucket my-data-bucket. The bucket does
NOT have a bucket policy granting Timestream s3:PutObject.
Database name IoTSensorData, region us-east-1. Memory store TTL
6h, magnetic store TTL 365d.
