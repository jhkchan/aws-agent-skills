# Worked Examples — s3-glacier-restore-operator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

### Worked example — Batch Operations bulk restore


```text
OPERATION: bulk-restore
VERDICT: COMPLETED
TARGET: batch-ops job 1234abcd-...
PRE_CHECKS:
  - [PASS] Manifest uploaded to batch-ops-manifests (10000 keys)
  - [PASS] IAM role S3BatchRestoreRole has s3:RestoreObject on
    prod-archive-bucket
  - [PASS] Report bucket batch-ops-reports exists
  - [PASS] All manifest keys verified in head-object sampling
STEPS:
  1. aws s3control create-job (Bulk tier, Days=30)
  2. aws s3control describe-job --job-id 1234abcd-...
POST_VERIFY:
  - [PASS] Job Status: Complete
  - [PASS] ProgressSummary.TotalTasks: 10000
  - [PASS] ProgressSummary.NumberSucceeded: 9998
  - [WARN] ProgressSummary.NumberFailed: 2 (NoSuchKey — see report)
STATE: complete — 9998 objects restored, 2 NoSuchKey failures in
       s3://batch-ops-reports/restore-2025-Q1/
NOTES:
  - Bulk tier SLA: 5-12 hr. Actual elapsed: 8.2 hr.
  - Re-run failed tasks with a filtered manifest if needed.
  - All restored objects revert to archive after 30 days.
```
