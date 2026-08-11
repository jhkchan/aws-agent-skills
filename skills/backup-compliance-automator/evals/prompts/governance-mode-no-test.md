# Eval prompt: governance-mode-no-test

Validate this existing AWS Backup compliance posture aligned to HIPAA.
Emit the standard Backup block (FRAMEWORK, REPORTING, LEGAL_HOLD,
CROSS_ACCOUNT, SEARCH, VERIFICATION, VERDICT, FINDINGS, REMEDIATION).

Current state:
- Compliance framework: HIPAA (claimed)
- Resources in scope: EC2, RDS, S3 (PHI workloads)
- Accounts scope: single account
- Existing posture:
  - Audit Manager framework: 3 controls only
    - BACKUP_PLAN_EXISTENCE
    - BACKUP_RESOURCES_PROTECTED_BY_BACKUP_PLAN
    - BACKUP_REPORT_LAST_BACKUP_AGE (maxAgeInDays=1)
    - MISSING: BACKUP_RECOVERY_POINT_ENCRYPTED control
    - MISSING: BACKUP_RECOVERY_POINT_MANUAL_DELETION_DISABLED control
  - Vault Lock: GOVERNANCE mode on production-vault (root can override
    retention with s3:PutBucketObjectLock privilege)
  - Legal hold: BackupLegalHold mechanism configured but never tested
    (no create + release cycle ever run)
  - Reports: monthly compliance only; no coverage report
    (unprotected resources are invisible)
  - Last restore drill: 14 months ago (HIPAA requires annual)
  - Latest compliance report: 2026-07-10 (31 days stale — manual
    cadence is unreliable)
  - Cost allocation tags: partially active (Project only,
    Environment missing)
  - No EventBridge Scheduler for periodic audits (runs are manual)

Expected: MANUAL_STEP_REQUIRED. The skill must flag multiple CRITICAL
gaps and produce specific remediation:
1. GOVERNANCE mode Vault Lock is not compliance-grade for HIPAA. Root
   can override retention. Must switch to LOCK_MODE (compliance mode)
   — verify in non-prod first, then promote.
2. Missing ENCRYPTED control — HIPAA requires at-rest encryption
   (CMK) on all recovery points. Add BACKUP_RECOVERY_POINT_ENCRYPTED.
3. Missing MANUAL_DELETION_DISABLED control — without it, manual
   deletes are not blocked.
4. Legal hold never tested — under court deadline pressure, the team
   will not know how to create or release holds. Run a quarterly
   create + release cycle on non-prod.
5. No restore drill in 14 months — recovery capability unverified.
   Run a restore drill on a tier-1 PHI resource within 30 days.
6. Stale compliance report (31 days old) — manual cadence is
   unreliable. Add EventBridge Scheduler for daily audit runs.
