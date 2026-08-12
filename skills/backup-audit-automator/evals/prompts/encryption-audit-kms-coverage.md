# Eval: encryption-audit-kms-coverage

**Difficulty:** medium
**Branch:** AUTOMATION_DEPLOYED — encryption audit verifying KMS key on all recovery points

## Prompt

Run a backup encryption audit across all my backup vaults. I
need to verify that every recovery point has KMS encryption.
If any recovery points are unencrypted, flag them. S3 report
delivery to s3://backup-audit-bucket/encryption/. Account:
123456789012. Region us-east-1.
