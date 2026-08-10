# Baseline (no-skill) response: large-job-billion-objects-ready

This file captures what a generic assistant produces WITHOUT the
s3-batch-operations-operator skill loaded.

---

For a billion-object re-encrypt job, you should split the work into
multiple smaller jobs. Create a Batch Operations job for each shard:

```bash
aws s3control create-job \
  --account-id 111111111111 \
  --region us-east-1 \
  --priority 50 \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOpsRole \
  --operation '{"S3Copy": {"TargetResource": "arn:aws:s3:::prod-data"}}' \
  --manifest '{"Spec":{"Format":"S3InventoryReport"},"Location":{"ObjectArn":"arn:aws:s3:::prod-inventory/shard-1/manifest.json"}}' \
  --report '{"Bucket":"arn:aws:s3:::prod-batch-reports","Format":"Report_CSV_20180820"}'
```

Repeat for each shard. Make sure the KMS quota is high enough for the
request volume.
