# Eval: missing-vpc-endpoint

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — VPC endpoint for S3 not present in target VPC

## Prompt

Create a VPC-only access point "internal-logs-ap" for bucket
"internal-logs" in account 123456789012 region us-west-2, VPC
vpc-998877. The bucket has BPA + SSE-S3. I checked and there is
no VPC endpoint for S3 in vpc-998877. Make the bucket truly
VPC-only.
