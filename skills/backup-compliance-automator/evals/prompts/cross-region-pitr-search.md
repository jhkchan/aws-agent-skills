# Eval prompt: cross-region-pitr-search

Design AWS Backup compliance automation for an eDiscovery workload.
Emit the standard Backup block (FRAMEWORK, REPORTING, LEGAL_HOLD,
CROSS_ACCOUNT, SEARCH, VERIFICATION, VERDICT, FINDINGS, REMEDIATION).

Requirements:
- Compliance framework: custom:ediscovery
- Resources in scope: DynamoDB (continuous backup / PITR), S3
- Accounts scope: single account
- Retention policy: 35d daily + 35d PITR continuous, immutable
- Audit Manager framework: ediscovery-backup with controls
  - BACKUP_PLAN_EXISTENCE
  - BACKUP_RECOVERY_POINT_ENCRYPTED
  - BACKUP_VARIANT_WITH_REGION_ISOLATION (us-east-1 -> us-west-2)
- Cross-region copy: us-east-1 -> us-west-2 org-compliance-vault
- Backup Search:
  - Scoped to DynamoDB tables (tight scope, not all vaults)
  - Search term matches case keywords (e.g., "acme-patent-dispute")
  - Results exported to S3 for legal team review
- Legal hold automation:
  - Lambda reads search results from S3
  - Batch creates BackupLegalHold on each matching recovery point
  - Case-ID convention documented
  - DLQ on the Lambda target
- Vault Lock: LOCK_MODE on ediscovery-vault, 35-2555d
- Reports: monthly compliance, weekly job summary, monthly coverage
- Restore drill: 2026-07-25, DynamoDB PITR restore to a specific
  timestamp, RTO measured and documented
- Cost tags: Case, Workload active in Billing

Expected: AUTOMATED. The playbook covers eDiscovery with PITR continuous
backup, scoped Backup Search (tight scope to control cost), search-
driven legal hold automation, LOCK_MODE Vault Lock, and a documented
restore drill.
