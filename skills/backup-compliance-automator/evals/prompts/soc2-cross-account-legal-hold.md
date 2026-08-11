# Eval prompt: soc2-cross-account-legal-hold

Design AWS Backup compliance automation for our 30-account org aligned to
SOC2. Emit the standard Backup block (FRAMEWORK, REPORTING, LEGAL_HOLD,
CROSS_ACCOUNT, SEARCH, VERIFICATION, VERDICT, FINDINGS, REMEDIATION).

Requirements:
- Compliance framework: SOC2
- Resources in scope: EC2, RDS, DynamoDB, S3
- Accounts scope: organizational (30 member accounts)
- Retention policy: 35d daily, 12m monthly, immutability required
- Legal hold required: yes (litigation hold on demand from the legal team)
- Audit Manager framework: custom soc2-backup-compliance with controls
  - BACKUP_PLAN_EXISTENCE
  - BACKUP_RESOURCES_PROTECTED_BY_BACKUP_PLAN
  - BACKUP_RECOVERY_POINT_MANUAL_DELETION_DISABLED
  - BACKUP_REPORT_LAST_BACKUP_AGE (maxAgeInDays=1)
  - BACKUP_RECOVERY_POINT_ENCRYPTED (CMK)
- Reports: monthly compliance, weekly job summary, weekly coverage,
  landing in versioned S3 bucket backup-compliance-reports/soc2/ with
  Object Lock GOVERNANCE 7-year retention
- Vault Lock: LOCK_MODE (compliance mode), 7-365d
- Legal hold automation:
  - EventBridge rule on custom.legal -> Lambda create-legal-hold
  - DLQ on the Lambda target (sqs legal-hold-dlq)
  - Quarterly test: create + release cycle on non-prod recovery point
  - Case-ID convention documented (e.g., "Acme v. Example - 2026-CV-1234")
- Cross-account: delegated admin in audit account 222222222222,
  org-compliance-vault with member access policy granting
  backup:CopyIntoBackupVault, COPY_ACTION in all 30 member plans
- Backup Search: scoped to production-vault + org-compliance-vault,
  eDiscovery workflow documented (search -> create-legal-hold)
- Cost allocation tags: Project, Environment, Compliance active in Billing
- Restore drill: 2026-07-20, EBS 1TB restore, RTO 35min measured
- EventBridge Scheduler: daily audit run at 02:00 UTC

Expected: AUTOMATED. The playbook covers SOC2 framework with all five
controls, LOCK_MODE Vault Lock, tested legal hold automation, cross-
account centralization via delegated admin + org vault, scoped Backup
Search, cost tags active, and restore drill within 90 days.
