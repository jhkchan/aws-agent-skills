# Baseline (no-skill) — full-deploy-with-replication

> This is the response a model produces **without** the skill definition.
> It lists replication commands but misses the IAM role trust policy,
> the KMS cross-region decrypt/encrypt permissions, BucketOwnerEnforced,
> S3 Bucket Keys, MFA Delete requiring root account, and the structured
> checklist.

---

To set up your backup bucket with cross-region replication:

1. Create the source bucket:
```bash
aws s3api create-bucket --bucket prod-backup-primary --region us-east-1
```

2. Create the destination bucket:
```bash
aws s3api create-bucket --bucket prod-backup-dr --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2
```

3. Enable versioning on both:
```bash
aws s3api put-bucket-versioning --bucket prod-backup-primary \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-versioning --bucket prod-backup-dr \
  --versioning-configuration Status=Enabled
```

4. Enable encryption:
```bash
aws s3api put-bucket-encryption --bucket prod-backup-primary \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"alias/prod-backup-key"}}]}'
```

5. Set up replication:
```bash
aws s3api put-bucket-replication --bucket prod-backup-primary \
  --replication-configuration '{"Role":"arn:aws:iam::123456789012:role/s3-replication","Rules":[{"Status":"Enabled","Prefix":"","Destination":{"Bucket":"arn:aws:s3:::prod-backup-dr"}}]}'
```

6. Add lifecycle:
```bash
aws s3api put-bucket-lifecycle-configuration --bucket prod-backup-primary \
  --lifecycle-configuration '{"Rules":[{"ID":"archive","Status":"Enabled","Filter":{"Prefix":""},"Transitions":[{"Days":90,"StorageClass":"GLACIER"},{"Days":180,"StorageClass":"DEEP_ARCHIVE"}]}]}'
```

For MFA delete you'd need to use the root account with an MFA device.

You'll also need to create an IAM role for replication and make sure
both KMS keys are accessible. Enable Block Public Access too.
