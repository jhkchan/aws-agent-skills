# Eval: missing-iam-role

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — IAM role NonExistentRole does not exist in source account 222222222222; DataZone cannot assume a nonexistent role

## Prompt

Create a DataZone domain called new-domain in us-east-1, account
111111111111. Project analytics. Add an S3 data source
my-data-bucket in source account 222222222222. The source
account IAM role is NonExistentRole. Tags: Environment=dev.
