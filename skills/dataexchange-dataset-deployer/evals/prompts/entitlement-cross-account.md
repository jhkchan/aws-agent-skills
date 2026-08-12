# Eval: entitlement-cross-account

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — entitlement as the sharing mechanism (NOT IAM), target account cited, receiving account exports to their S3 bucket

## Prompt

Share Data Exchange data set ds-share789 with AWS account
999999999999 via entitlement. The data set is S3_SNAPSHOT type.
Provider account is 123456789012 in us-east-1. After the
entitlement is created, the receiving account should export
to bucket their-dx-bucket. Tags: Environment=production,
SharedWith=partner.
