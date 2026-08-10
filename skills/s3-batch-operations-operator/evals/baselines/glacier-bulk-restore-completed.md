# Baseline (no-skill) response: glacier-bulk-restore-completed

This file captures what a generic assistant produces WITHOUT the
s3-batch-operations-operator skill loaded.

---

The Glacier bulk restore job has completed successfully. All 2,300,000
tasks succeeded with zero failures. You can verify the job status with:

```bash
aws s3control describe-job \
  --account-id 111111111111 \
  --job-id a1b2c3d4-5678-90ef-ghij-klmnopqrstuv
```

The objects will be available for the duration specified in
`ExpirationInDays` (30 days). Note that Bulk tier restores can take
several hours to materialize.
