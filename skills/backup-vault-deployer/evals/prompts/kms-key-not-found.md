# Eval: kms-key-not-found

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — KMS key alias/nonexistent-key does not exist; vault creation would fail

## Prompt

Create an AWS Backup vault named production-vault in us-east-1
account 123456789012. Use KMS key alias/nonexistent-key. The key
does not exist — aws kms describe-key returns NotFoundException.
Create a backup plan with daily schedule. Compliance-mode vault
lock with MinRetentionDays=30.
