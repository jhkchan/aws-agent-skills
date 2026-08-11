# Baseline (no-skill) response: hipaa-vault-lock-test

This file captures what a generic assistant produces WITHOUT the
backup-compliance-automator skill loaded.

---

For HIPAA backup compliance, you should encrypt all backups with a KMS
key and configure Vault Lock on your backup vault to prevent deletion
during the retention period. Schedule monthly compliance reports and
run restore tests annually to verify recovery works.

Document the legal hold workflow so the team knows how to use it if
litigation arises.

---

Notes on what the baseline misses:

- Does NOT specify LOCK_MODE (compliance mode) for Vault Lock — may
  default to GOVERNANCE, which allows root override. HIPAA requires
  LOCK_MODE.
- Does NOT specify CMK encryption (vs AWS-managed default key) —
  HIPAA requires customer-managed keys.
- Does NOT mention testing the legal hold workflow — the first hold
  should not be under court deadline pressure.
- Does NOT include the BACKUP_RECOVERY_POINT_ENCRYPTED control in the
  Audit Manager framework.
- Does NOT specify a quarterly (vs annual) restore drill cadence.
- Does NOT mention activating cost allocation tags in Billing.
