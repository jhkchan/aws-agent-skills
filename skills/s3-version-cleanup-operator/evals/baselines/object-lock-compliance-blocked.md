# Baseline (no-skill) response: object-lock-compliance-blocked

This file captures what a generic assistant produces WITHOUT the
s3-version-cleanup-operator skill loaded.

---

You can clean up the noncurrent versions in your compliance archive
bucket with S3 Batch Operations. First generate a manifest from S3
Inventory, then create a job to delete the versions:

```bash
aws s3control create-job \
  --account-id 111111111111 \
  --operation '{"S3DeleteObjectVersion": {}}' \
  --manifest '{"Spec": {"Format": "S3InventoryReports", "Bucket": "arn:aws:s3:::manifest-bucket", "Prefix": "compliance-archive-inventory/2026-08-08/"}, "Location": {"ObjectArn": "arn:aws:s3:::manifest-bucket/compliance-archive-inventory/2026-08-08/manifest.json"}}' \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOperationsDeleteRole \
  --report '{"Bucket":"arn:aws:s3:::batch-ops-reports","Format":"Report_CSV_20180820","Enabled":true,"ReportScope":"AllTasks"}' \
  --priority 50
```

This will delete the 10,000 noncurrent versions. Monitor the job with
`aws s3control describe-job`.
