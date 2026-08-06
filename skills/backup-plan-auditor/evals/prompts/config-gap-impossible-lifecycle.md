# Eval prompt: config-gap-impossible-lifecycle

Audit the following AWS Backup plan configuration for coverage gaps, vault
risks, lifecycle issues, and compliance violations. Emit the standard
VERDICT block (PLAN, VERDICT, REASON, FINDINGS, REMEDIATION).

Plan name: cold-storage-backup
Plan ARN: arn:aws:backup:us-east-1:111111111111:backup-plan:jkl-012

Backup vault: compliant-vault
Vault lock: COMPLIANCE (MinRetentionDays: 30)
Vault encryption key: arn:aws:kms:us-east-1:111111111111:key/cmk-efs (customer-managed CMK)

Backup plan rules:
  Rule 1 (efs-cold-tier):
    ScheduleExpression: cron(0 3 * * ? *)  — daily at 03:00 UTC
    TargetBackupVault: compliant-vault
    Lifecycle:
      MoveToColdStorageAfterDays: 90
      DeleteAfterDays: 30

Backup selections:
  Selection 1 (efs-prod):
    IamRoleArn: arn:aws:iam::111111111111:role/service-role/AWSBackupDefaultServiceRole
    Resources:
      - arn:aws:elasticfilesystem:us-east-1:111111111111:file-system/fs-abc12345
    Conditions: (none)
