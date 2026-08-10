# Baseline (no-skill) response: batch-replicate-existing-objects-ready

This file captures what a generic assistant produces WITHOUT the
s3-replication-operator skill loaded.

---

To replicate existing objects using S3 Batch Operations, first generate
a CSV manifest listing the objects to replicate, then create a Batch
Operations job:

```bash
aws s3control create-job \
  --account-id 111111111111 \
  --operation '{"S3ReplicateObject": {}}' \
  --manifest '{"Spec": {"Format": "S3BatchOperations_CSV_20180820", "Fields": ["Bucket", "Key"]}, "Location": {"ObjectArn": "arn:aws:s3:::prod-logs-inventory-prod/inv/manifest.csv", "ETag": "<etag>"}}' \
  --report '{"Bucket": "arn:aws:s3:::prod-logs-batch-reports", "Format": "Report_CSV_20180820", "Enabled": true}' \
  --role-arn arn:aws:iam::111111111111:role/s3-batch-repl-role
```

The job will replicate each object listed in the manifest. Monitor
progress with `aws s3control describe-job`.
