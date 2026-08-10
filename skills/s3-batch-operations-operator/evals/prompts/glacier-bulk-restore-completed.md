# Eval prompt: glacier-bulk-restore-completed

Plan and verify the following S3 Batch Operations Glacier bulk restore
job (post-execution form) and emit the standard VERDICT block
(OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, NOTES).
The job has already executed; produce the post-verification COMPLETED
form.

Operation: create-job (post-verification)
JobId: a1b2c3d4-5678-90ef-ghij-klmnopqrstuv
Manifest: s3://archive-inventory/2026-07-15/manifest.json (2,300,000 objects)
Operation type: S3InitiateRestoreObject (GlacierJobTier: BULK, ExpirationInDays: 30)

```json
{
  "JobDescriptor": {
    "JobId": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv",
    "Status": "Complete",
    "ProgressSummary": {
      "NumberOfTasksSucceeded": 2300000,
      "NumberOfTasksFailed": 0,
      "TotalNumberOfTasks": 2300000
    }
  },
  "CompletionReport": {
    "Scope": "FailedTasksOnly",
    "Content": "empty file (no failures)"
  },
  "SampleVerification": {
    "Method": "head-object --restore on 5 random objects",
    "Result": "all show ongoing-request=\"true\", expiry in 48h",
    "Note": "Expected for Bulk tier — restore is asynchronous"
  }
}
```
