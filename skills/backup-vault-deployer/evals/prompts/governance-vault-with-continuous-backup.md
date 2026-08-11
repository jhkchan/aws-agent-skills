# Eval: governance-vault-with-continuous-backup

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — governance-mode vault lock (soft protection), continuous backup for EC2/EFS (PITR), periodic for S3, resource-ARN selection, no cross-region copy

## Prompt

Create an AWS Backup vault named dev-backup-vault in us-east-1
account 123456789012. Use KMS key alias/dev-backup-key
(customer-managed, enabled). Apply vault lock in GOVERNANCE mode
with MinRetentionDays=7, MaxRetentionDays=90. Create a backup
plan named dev-continuous-backup with schedule cron(0 2 ? * * *)
targeting this vault, lifecycle DeleteAfterDays=30. Continuous
backup for EC2 and EFS (RecoveryPointType=CONTINUOUS). Periodic
for S3. Resource-ARN selection for 10 EC2 instances and 3 EFS
filesystems. No cross-region copy needed. Tags:
Environment=development.
