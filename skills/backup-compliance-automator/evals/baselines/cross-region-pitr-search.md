# Baseline (no-skill) response: cross-region-pitr-search

This file captures what a generic assistant produces WITHOUT the
backup-compliance-automator skill loaded.

---

For eDiscovery backup compliance, enable point-in-time recovery (PITR)
on your DynamoDB tables and configure a backup plan with cross-region
copies to a secondary region. Use AWS Backup Search to find recovery
points matching case keywords, then apply legal holds on the matching
ones.

Schedule monthly compliance reports to verify the plan is working.

---

Notes on what the baseline misses:

- Does NOT scope Backup Search tightly — broad searches across years
  of backups are expensive per GB scanned. The skill requires tight
  scoping (vault, resource type, date range).
- Does NOT detail the Lambda workflow that reads search results from
  S3 and batch-creates legal holds.
- Does NOT mention LOCK_MODE (compliance mode) for Vault Lock.
- Does NOT specify a DLQ on the legal hold Lambda target.
- Does NOT document a case-ID convention for hold titles (traceability).
- Does NOT include the cross-region isolation control
  (BACKUP_VARIANT_WITH_REGION_ISOLATION) in the Audit Manager framework.
