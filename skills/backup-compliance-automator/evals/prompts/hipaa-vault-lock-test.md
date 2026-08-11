# Eval prompt: hipaa-vault-lock-test

Design AWS Backup compliance automation for a single account aligned to
HIPAA. Emit the standard Backup block (FRAMEWORK, REPORTING, LEGAL_HOLD,
CROSS_ACCOUNT, SEARCH, VERIFICATION, VERDICT, FINDINGS, REMEDIATION).

Requirements:
- Compliance framework: HIPAA
- Resources in scope: EC2, RDS, S3 (PHI workloads)
- Accounts scope: single account
- Retention policy: 365d daily, immutability required, CMK encryption
- Audit Manager framework: hipaa-backup with controls
  - BACKUP_RECOVERY_POINT_ENCRYPTED (CMK required, not AWS-managed)
  - BACKUP_RECOVERY_POINT_MANUAL_DELETION_DISABLED
  - BACKUP_RECOVERY_POINT_MINIMUM_RETENTION (MinRetentionDays=365)
  - BACKUP_REPORT_LAST_BACKUP_AGE (maxAgeInDays=1)
  - BACKUP_REPORT_LAST_RESTORE_AGE (maxAgeInDays=90)
- Vault Lock: LOCK_MODE (compliance mode) on phi-prod-vault, 7-3650d
- Legal hold:
  - BackupLegalHold mechanism documented
  - Test cycle: 2026-07-15, create + release on non-prod recovery point
  - Cancel description includes case ID and closure date
- Reports: monthly compliance, weekly job summary, lands in versioned
  S3 bucket with Object Lock
- Restore drill: 2026-07-20, RDS PITR restore test, RTO 25min measured
- Cost tags: PHI, Workload active in Billing
- EventBridge Scheduler: daily audit run at 03:00 UTC

Expected: AUTOMATED. The playbook covers HIPAA with the encryption
control (CMK), LOCK_MODE Vault Lock (not GOVERNANCE), legal hold test
cycle completed within the last 90 days, restore drill within 90 days,
and active cost allocation tags.
