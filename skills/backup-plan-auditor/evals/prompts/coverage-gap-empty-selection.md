# Eval prompt: coverage-gap-empty-selection

Audit the following AWS Backup plan configuration for coverage gaps, vault
risks, lifecycle issues, and compliance violations. Emit the standard
VERDICT block (PLAN, VERDICT, REASON, FINDINGS, REMEDIATION).

Plan name: daily-ec2-backup
Plan ARN: arn:aws:backup:us-east-1:111111111111:backup-plan:abc-123

Backup vault: secure-vault
Vault lock: COMPLIANCE (MinRetentionDays: 30)
Vault encryption key: arn:aws:kms:us-east-1:111111111111:key/cmk-vault (customer-managed CMK)

Backup plan rules:
  Rule 1 (daily-rule):
    ScheduleExpression: cron(0 5 * * ? *)  — daily at 05:00 UTC
    TargetBackupVault: secure-vault
    Lifecycle: DeleteAfterDays: 30

Backup selections:
  Selection 1 (ec2-prod):
    IamRoleArn: arn:aws:iam::111111111111:role/service-role/AWSBackupDefaultServiceRole
    Resources: []  (empty — no resources assigned)
    ListOfTags: (none)
    Conditions: (none)
