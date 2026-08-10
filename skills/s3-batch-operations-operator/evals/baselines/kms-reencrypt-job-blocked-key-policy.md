# Baseline (no-skill) response: kms-reencrypt-job-blocked-key-policy

This file captures what a generic assistant produces WITHOUT the
s3-batch-operations-operator skill loaded.

---

To re-encrypt the objects with a new KMS key, you can create a Batch
Operations copy job that overwrites the source in place:

```bash
aws s3control create-job \
  --account-id 111111111111 \
  --region us-east-1 \
  --priority 50 \
  --role-arn arn:aws:iam::111111111111:role/S3BatchOpsRole \
  --operation '{"S3Copy": {"TargetResource": "arn:aws:s3:::prod-data"}}' \
  --manifest '{"Spec":{"Format":"S3InventoryReport"},"Location":{"ObjectArn":"arn:aws:s3:::prod-inventory/2026-08-01/manifest.json"}}' \
  --report '{"Bucket":"arn:aws:s3:::prod-batch-reports","Format":"Report_CSV_20180820"}'
```

Make sure the role has `kms:Decrypt` on the old key and `kms:Encrypt`
on the new key. You may need to update the key policy of the new KMS
key to allow the role.
