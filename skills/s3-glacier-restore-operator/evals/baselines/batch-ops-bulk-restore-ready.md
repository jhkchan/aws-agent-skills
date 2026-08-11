# Baseline (no-skill) response: batch-ops-bulk-restore-ready

This file captures what a generic assistant produces WITHOUT the
s3-glacier-restore-operator skill loaded.

---

You can use S3 Batch Operations to bulk-restore:

```bash
aws s3control create-job \
  --account-id 111111111111 \
  --priority 1 \
  --role-arn arn:aws:iam::111111111111:role/S3BatchRestoreRole \
  --operation '{"S3RestoreObject": {"Days": 30, "GlacierJobParameters": {"Tier": "Bulk"}}}' \
  --manifest file://manifest-config.json \
  --report file://report-config.json
```

Then describe the job to monitor progress:

```bash
aws s3control describe-job --account-id 111111111111 --job-id <id>
```
