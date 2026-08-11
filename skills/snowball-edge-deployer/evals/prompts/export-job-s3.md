# Eval: export-job-s3

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — export job, data pre-loaded by AWS before shipping, source bucket noted

## Prompt

Create a Snowball Edge export job to download 60 TB of data
from S3 bucket my-export-bucket in us-east-1 to on-premises.
Shipping address: addr-export01. Device type: Edge Storage
Optimized. Shipping option: NEXT_DAY. Tags: Environment=export,
Project=data-distribution.
