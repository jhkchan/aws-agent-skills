# Baseline (no-skill) — data-lake-intelligent-tiering

> This is the response a model produces **without** the skill definition.
> It mentions Intelligent-Tiering and SSE-KMS but misses BucketOwnerEnforced,
> S3 Bucket Keys, the HTTPS + SSE-KMS enforcement policy, and the structured
> checklist format.

---

To set up your data lake bucket:

```bash
# Create bucket
aws s3api create-bucket --bucket datalake-raw-zone --region us-east-1

# Encryption
aws s3api put-bucket-encryption --bucket datalake-raw-zone \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"alias/datalake-kms-key"}}]}'

# Versioning
aws s3api put-bucket-versioning --bucket datalake-raw-zone \
  --versioning-configuration Status=Enabled

# Intelligent-Tiering lifecycle
aws s3api put-bucket-lifecycle-configuration --bucket datalake-raw-zone \
  --lifecycle-configuration '{"Rules":[{"ID":"intelligent-tiering","Status":"Enabled","Filter":{"Prefix":""},"Transitions":[{"Days":0,"StorageClass":"INTELLIGENT_TIERING"}]}]}'

# Access logging
aws s3api put-bucket-logging --bucket datalake-raw-zone \
  --bucket-logging-status '{"LoggingEnabled":{"TargetBucket":"datalake-logs","TargetPrefix":"raw-zone/"}}'

# Tags
aws s3api put-bucket-tagging --bucket datalake-raw-zone \
  --tagging '{"TagSet":[{"Key":"Environment","Value":"production"},{"Key":"Workload","Value":"data-lake"}]}'
```

You might also want to enable Block Public Access.
