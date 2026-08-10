# Baseline (no-skill) response: batch-ops-immediate-cleanup-ready

This file captures what a generic assistant produces WITHOUT the
s3-version-cleanup-operator skill loaded.

---

You can clean up the 2.5M noncurrent versions with S3 Batch Operations:

```bash
aws s3control create-job \
  --account-id 111111111111 \
  --operation '{"S3DeleteObjectVersion": {}}' \
  --manifest '{"Spec": {"Format": "S3InventoryReports", "Bucket": "arn:aws:s3:::manifest-bucket", "Prefix": "staging-uploads-inventory/2026-08-08/"}, "Location": {"ObjectArn": "arn:aws:s3:::manifest-bucket/staging-uploads-inventory/2026-08-08/manifest.json"}}' \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOperationsDeleteRole
```

Wait for the job to complete via `aws s3control describe-job`.
