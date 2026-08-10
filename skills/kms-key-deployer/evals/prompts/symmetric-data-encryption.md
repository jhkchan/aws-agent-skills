# Eval: symmetric-data-encryption

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — symmetric CMK, separated admins/users, rotation, alias

## Prompt

Provision a customer-managed KMS key for production data
encryption in us-east-1. Alias: alias/payments-cmk. Workload:
encrypt EBS volumes, S3 objects, and Secrets Manager secrets
for the payments service. Key administrators: the kms-admin
IAM role. Key users: the payments-svc IAM role. Enable annual
automatic rotation. Deletion window: 30 days. Tags:
Environment=production, Application=payments. Account:
123456789012.
