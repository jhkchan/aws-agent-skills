# Eval prompt: ok-well-configured

Audit the following AWS Backup plan configuration for coverage gaps, vault
risks, lifecycle issues, and compliance violations. Emit the standard
VERDICT block (PLAN, VERDICT, REASON, FINDINGS, REMEDIATION).

Plan name: prod-compliant-backup
Plan ARN: arn:aws:backup:us-east-1:111111111111:backup-plan:mno-345

Backup vault: prod-locked-vault
Vault lock: COMPLIANCE (MinRetentionDays: 90, MaxRetentionDays: 365)
Vault encryption key: arn:aws:kms:us-east-1:111111111111:key/cmk-secure (customer-managed CMK)

Backup plan rules:
  Rule 1 (daily-production):
    ScheduleExpression: cron(0 2 * * ? *)  — daily at 02:00 UTC
    TargetBackupVault: prod-locked-vault
    Lifecycle:
      MoveToColdStorageAfterDays: 30
      DeleteAfterDays: 90
    CopyActions:
      - DestinationBackupVaultArn: arn:aws:backup:us-west-2:111111111111:backup-vault:dr-locked-vault
        Lifecycle:
          DeleteAfterDays: 90

Backup selections:
  Selection 1 (prod-resources):
    IamRoleArn: arn:aws:iam::111111111111:role/service-role/AWSBackupDefaultServiceRole
    Resources:
      - arn:aws:ec2:us-east-1:111111111111:instance/i-prod001
      - arn:aws:rds:us-east-1:111111111111:db:prod-db-001
      - arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders
    Conditions: (none)
