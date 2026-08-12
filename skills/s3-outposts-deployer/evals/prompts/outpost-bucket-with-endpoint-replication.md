# Eval: outpost-bucket-with-endpoint-replication

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — outpost bucket with endpoint, access point, replication, SSE-S3, versioning

## Prompt

Create an S3 bucket on Outpost op-0abc123def456. Bucket name:
my-outpost-bucket. I need a VPC endpoint in subnet subnet-abc123
with security group sg-outpost-s3. Access point my-ap in VPC
vpc-abc123. Replicate to cloud bucket s3://cloud-dr-bucket for
DR. Versioning enabled. Account: 123456789012. Region us-east-1.
Tags: Environment=onprem, Application=data-lake.
