# Baseline (no-skill) response: legal-hold-blocks-batch-delete

This file captures what a generic assistant produces WITHOUT the
s3-version-cleanup-operator skill loaded.

---

You can delete the 1,000 noncurrent versions with S3 Batch Operations:

```bash
aws s3control create-job \
  --account-id 111111111111 \
  --operation '{"S3DeleteObjectVersion": {}}' \
  --manifest '{"Spec": {"Format": "S3InventoryReports", "Bucket": "arn:aws:s3:::manifest-bucket", "Prefix": "litigation-hold-inventory/2026-08-08/"}, "Location": {"ObjectArn": "arn:aws:s3:::manifest-bucket/litigation-hold-inventory/2026-08-08/manifest.json"}}' \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOperationsDeleteRole
```

The job will process all 1,000 versions. Review the report for any
failures.
