# Baseline (no-skill) — secure-compliance-bucket

> This is the response a model produces **without** the skill definition.
> It lists some AWS CLI commands but misses the ordered provisioning
> procedure, the BucketOwnerEnforced default, S3 Bucket Keys, the SSE-KMS
> upload enforcement policy, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

To create a compliance S3 bucket, you'll want to run these commands:

1. Create the bucket:
```bash
aws s3api create-bucket --bucket compliance-archive-2024 --region us-east-1
```

2. Enable encryption:
```bash
aws s3api put-bucket-encryption --bucket compliance-archive-2024 \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"alias/compliance-s3-key"}}]}'
```

3. Enable versioning:
```bash
aws s3api put-bucket-versioning --bucket compliance-archive-2024 \
  --versioning-configuration Status=Enabled
```

4. Enable access logging:
```bash
aws s3api put-bucket-logging --bucket compliance-archive-2024 \
  --bucket-logging-status '{"LoggingEnabled":{"TargetBucket":"s3-access-logs-prod","TargetPrefix":"compliance/"}}'
```

5. Set up lifecycle:
```bash
aws s3api put-bucket-lifecycle-configuration --bucket compliance-archive-2024 \
  --lifecycle-configuration '{"Rules":[{"ID":"archive","Status":"Enabled","Filter":{"Prefix":""},"Transitions":[{"Days":30,"StorageClass":"STANDARD_IA"},{"Days":90,"StorageClass":"GLACIER"},{"Days":365,"StorageClass":"DEEP_ARCHIVE"}]}]}'
```

6. Add tags:
```bash
aws s3api put-bucket-tagging --bucket compliance-archive-2024 \
  --tagging '{"TagSet":[{"Key":"Environment","Value":"production"}]}'
```

For MFA delete you need to use the root account. For CloudTrail data
events, configure that in the CloudTrail console.

Make sure to also enable Block Public Access in the console.
