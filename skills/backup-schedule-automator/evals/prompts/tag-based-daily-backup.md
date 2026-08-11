# Eval prompt: tag-based-daily-backup

Design an automated AWS Backup schedule for the following workload.
Emit the standard BACKUP block (PLAN, VAULT, LIFECYCLE, TRIGGER,
RESTORE_TEST, TAG_SCOPE, CROSS_ACCOUNT, CROSS_REGION, VERDICT, TEMPLATE).

Design reference: tag-based-daily-backup
Account: 111111111111
Region: us-east-1

Resources: DynamoDB tables and EBS volumes tagged
  backup-plan=daily-prod, environment=prod
Backup frequency: Daily at 05:00 UTC
Retention: 30 days hot, 90 days cold (lifecycle tiering)
Vault: prod-backup-vault (named, with access policy)
Cross-region copy: us-west-2 dr-vault (90-day retention)
IAM role: arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole
Pre-prod validation: completed (5 resources tested, all backed up and
restored successfully).
