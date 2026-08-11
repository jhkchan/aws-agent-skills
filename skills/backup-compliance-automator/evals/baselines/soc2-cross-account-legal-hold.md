# Baseline (no-skill) response: soc2-cross-account-legal-hold

This file captures what a generic assistant produces WITHOUT the
backup-compliance-automator skill loaded.

---

To set up SOC2 backup compliance for your 30-account org, you'll want
to use AWS Backup Audit Manager to create a framework with controls for
plan existence and resources protected. Schedule monthly compliance
reports to land in an S3 bucket.

For legal hold, use the BackupLegalHold resource to freeze recovery
points when needed. You can trigger this with an EventBridge rule and
a Lambda function.

For cross-account, use AWS Organizations to delegate an administrator
account and create an org-wide backup vault. Member accounts can copy
their backups to the central vault.

Run a restore test periodically to verify recovery works.

---

Notes on what the baseline misses:

- Does NOT specify LOCK_MODE (compliance mode) for Vault Lock — may
  default to GOVERNANCE mode, which fails SOC2 audit.
- Does NOT mention the encryption control (BACKUP_RECOVERY_POINT_ENCRYPTED)
  — an unencrypted recovery point is a SOC2 finding.
- Does NOT mention testing the legal hold workflow quarterly — the
  team's first hold would be under court deadline pressure.
- Does NOT specify the backup:CopyIntoBackupVault vault access policy
  required for cross-account copies to succeed.
- Does NOT mention activating cost allocation tags in Billing before
  they appear in Cost Explorer.
- Does NOT scope Backup Search tightly — broad searches are expensive
  per GB scanned.
- Does NOT include restore drill controls (BACKUP_REPORT_LAST_RESTORE_AGE).
