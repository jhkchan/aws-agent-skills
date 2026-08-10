# Baseline (no-skill) response: create-copy-job-inventory-manifest-ready

This file captures what a generic assistant produces WITHOUT the
s3-batch-operations-operator skill loaded.

---

To create a Batch Operations copy job for the re-encrypt, use the
following command:

```bash
aws s3control create-job \
  --account-id 111111111111 \
  --region us-east-1 \
  --priority 50 \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOpsRole \
  --operation '{"S3Copy": {}}' \
  --manifest '{"Spec":{"Format":"S3InventoryReport"},"Location":{"ObjectArn":"arn:aws:s3:::prod-inventory/2026-08-01/manifest.json"}}' \
  --report '{"Bucket":"arn:aws:s3:::prod-batch-reports","Format":"Report_CSV_20180820","ReportScope":"Task"}'
```

Make sure the role has the necessary S3 and KMS permissions. After
the job is created, you can check its status with `describe-job`.
