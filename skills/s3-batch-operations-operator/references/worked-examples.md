# Worked Examples — S3 Batch Operations Operator

Load-on-demand worked examples moved verbatim from SKILL.md (the
primary create-job KMS re-encrypt example stays in SKILL.md).

## Worked example — diagnose-job (BLOCKED with remediation)

```text
OPERATION: diagnose-job
VERDICT: BLOCKED
TARGET: job a1b2c3d4-5678-90ef-ghij-klmnopqrstuv
        (operation: Invoke, status: Complete with 8,400 failures)
PRE_CHECKS:
  - [PASS] Job exists, Status: Complete
  - [PASS] Report bucket readable
  - [FAIL] 8,400 tasks failed with ResourceConflictException
    (Lambda reserved concurrency exhausted)
  - [PASS] Manifest readable, format CSV
STEPS: (none — root cause is Lambda reserved concurrency)
POST_VERIFY: (none)
NOTES:
  - Root cause: Lambda MyObjectProcessor has ReservedConcurrentExecutions=10,
    but the Batch Operations job ran at RequestsPerSecond=100. Every
    invocation beyond 10 was throttled, producing ResourceConflictException
    in the completion report.
  - Fix: raise reserved concurrency to at least the RPS, or lower RPS.
    Option A (raise concurrency):
      aws lambda put-function-concurrency \
        --function-name MyObjectProcessor \
        --reserved-concurrent-executions 100
    Option B (lower RPS): create a new job with the failed-objects
      manifest at RequestsPerSecond=10.
  - Re-run the failed objects only: extract the FAILED entries from
    the completion report into a new CSV manifest, create a new job.
```

## Worked example — create-job (Glacier bulk restore, COMPLETED)

```text
OPERATION: create-job
VERDICT: COMPLETED
TARGET: s3://archive-inventory/2026-07-15/manifest.json
        (operation: S3InitiateRestoreObject, GlacierJobTier: Bulk)
PRE_CHECKS:
  - [PASS] Manifest readable, 2,300,000 objects
  - [PASS] All source objects in GLACIER (verified via inventory)
  - [PASS] Role has s3:RestoreObject on archive-bucket
  - [PASS] RequestsPerSecond: 1000
STEPS:
  1. (executed) aws s3control create-job ... --operation \
       '{"S3InitiateRestoreObject":{"ExpirationInDays":30,"GlacierJobTier":"BULK"}}'
  2. (executed) Polled describe-job every 5 min for 4 hours until Complete
POST_VERIFY:
  - [PASS] Status: Complete, NumberOfTasksSucceeded: 2,300,000,
    NumberOfTasksFailed: 0
  - [PASS] Completion report (FailedTasksOnly): empty file
  - [PASS] Sample 5 objects: head-object --restore shows
    ongoing-request="true" with expiry in 48h (Bulk tier expected)
NOTES:
  - Glacier Bulk restore can take up to 12 hours to materialize.
    Status: Complete means restore REQUESTS were submitted, not that
    objects are restored. Poll head-object --restore on a sample
    before downstream processing.
```
