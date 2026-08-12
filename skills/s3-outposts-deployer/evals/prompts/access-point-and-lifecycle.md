# Eval: access-point-and-lifecycle

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — access point, lifecycle expiration (no Glacier on Outpost), versioning

## Prompt

Create an S3 bucket on Outpost op-0def456ghi. Bucket name:
lifecycle-bucket. Access point lifecycle-ap in VPC vpc-def456.
Endpoint in subnet subnet-def456 with SG sg-lifecycle-s3. I
need a lifecycle rule to expire objects after 90 days. Versioning
enabled. Account: 123456789012. Region us-east-1.
