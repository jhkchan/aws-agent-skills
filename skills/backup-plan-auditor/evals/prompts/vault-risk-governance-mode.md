# Eval prompt: vault-risk-governance-mode

Audit the following AWS Backup plan configuration for coverage gaps, vault
risks, lifecycle issues, and compliance violations. Emit the standard
VERDICT block (PLAN, VERDICT, REASON, FINDINGS, REMEDIATION).

Plan name: staging-backup-plan
Plan ARN: arn:aws:backup:us-east-1:111111111111:backup-plan:pqr-678

Backup vault: staging-vault
Vault lock: GOVERNANCE (MinRetentionDays: 30, ChangeableForDays: 30 — lock becomes permanent in 30 days)
Vault encryption key: arn:aws:kms:us-east-1:111111111111:key/cmk-staging (customer-managed CMK)

Backup plan rules:
  Rule 1 (staging-daily):
    ScheduleExpression: cron(0 4 * * ? *)  — daily at 04:00 UTC
    TargetBackupVault: staging-vault
    Lifecycle: DeleteAfterDays: 30

Backup selections:
  Selection 1 (staging-ec2):
    IamRoleArn: arn:aws:iam::111111111111:role/service-role/AWSBackupDefaultServiceRole
    Resources:
      - arn:aws:ec2:us-east-1:111111111111:instance/i-staging001
    Conditions: (none)
