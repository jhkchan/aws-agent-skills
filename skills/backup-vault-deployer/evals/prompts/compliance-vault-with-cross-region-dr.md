# Eval: compliance-vault-with-cross-region-dr

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — compliance-mode vault lock, customer-managed KMS, daily backup plan with lifecycle within lock window, cross-region copy to us-west-2 with destination vault and key ready, continuous backup for RDS/DynamoDB, tag-based selection, report plan

## Prompt

Create an AWS Backup vault named production-backup-vault in
us-east-1 account 123456789012. Use KMS key
alias/backup-encryption-key (customer-managed, enabled). Apply
vault lock in COMPLIANCE mode with MinRetentionDays=90 and
MaxRetentionDays=365, ChangeableForDays=3. Create a backup plan
named production-daily-backup with schedule cron(0 5 ? * MON-SAT *)
targeting this vault, lifecycle DeleteAfterDays=180,
MoveToColdStorageAfterDays=60. Cross-region copy to vault
dr-backup-vault in us-west-2 (destination vault exists, KMS key
alias/dr-encryption-key accessible). Continuous backup for RDS
and DynamoDB resources (RecoveryPointType=CONTINUOUS). Tag-based
selection (Backup=daily) matching 45 resources. Report plan to
S3 bucket backup-compliance-reports. Tags: Environment=production,
Compliance=PCI-DSS.
