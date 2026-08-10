# Eval: missing-root-break-glass

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — root break-glass required

## Prompt

Provision a customer-managed KMS key in us-east-1. Alias:
alias/audit-cmk. The intended key policy grants kms:Encrypt,
kms:Decrypt, kms:GenerateDataKey*, and kms:* (admin) to the
audit-team IAM role, but does NOT include the account root as
a break-glass principal. Workload: encrypt audit logs in S3.
Deletion window: 7 days. Account: 123456789012.
