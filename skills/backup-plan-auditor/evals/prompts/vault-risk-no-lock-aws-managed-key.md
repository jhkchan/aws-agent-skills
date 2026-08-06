# Eval prompt: vault-risk-no-lock-aws-managed-key

Audit the following AWS Backup plan configuration for coverage gaps, vault
risks, lifecycle issues, and compliance violations. Emit the standard
VERDICT block (PLAN, VERDICT, REASON, FINDINGS, REMEDIATION).

Plan name: prod-database-backup
Plan ARN: arn:aws:backup:us-east-1:111111111111:backup-plan:def-456

Backup vault: prod-backup-vault
Vault lock: NONE
Vault encryption key: aws/backup (AWS-managed key — shared across all accounts in the region)

Backup plan rules:
  Rule 1 (daily-db):
    ScheduleExpression: cron(0 2 * * ? *)  — daily at 02:00 UTC
    TargetBackupVault: prod-backup-vault
    Lifecycle: DeleteAfterDays: 30

Backup selections:
  Selection 1 (rds-prod):
    IamRoleArn: arn:aws:iam::111111111111:role/service-role/AWSBackupDefaultServiceRole
    Resources:
      - arn:aws:rds:us-east-1:111111111111:db:prod-database-1
    Conditions: (none)
