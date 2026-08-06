# Eval prompt: noncompliant-weekly-short-retention

Audit the following AWS Backup plan configuration for coverage gaps, vault
risks, lifecycle issues, and compliance violations. Emit the standard
VERDICT block (PLAN, VERDICT, REASON, FINDINGS, REMEDIATION).

Plan name: weekly-archive-plan
Plan ARN: arn:aws:backup:us-east-1:111111111111:backup-plan:ghi-789

Backup vault: locked-vault
Vault lock: COMPLIANCE (MinRetentionDays: 7)
Vault encryption key: arn:aws:kms:us-east-1:111111111111:key/cmk-arch (customer-managed CMK)

Backup plan rules:
  Rule 1 (weekly-rule):
    ScheduleExpression: cron(0 5 ? * 1 *)  — every Monday at 05:00 UTC (weekly)
    TargetBackupVault: locked-vault
    Lifecycle: DeleteAfterDays: 7

Backup selections:
  Selection 1 (ec2-archive):
    IamRoleArn: arn:aws:iam::111111111111:role/service-role/AWSBackupDefaultServiceRole
    Resources:
      - arn:aws:ec2:us-east-1:111111111111:instance/i-abc12345
    Conditions: (none)
