# Baseline (no-skill) — sse-config-insight-suppress-or-implement

> This is the response a model produces **without** the skill definition.
> It enables SSE-S3 (AES256) instead of SSE-KMS with the customer CMK
> that the recommendation specifies, missing the compliance distinction.
> Generated for with-skill-vs-baseline comparison.

---

The DevOps Guru insight shows the S3 bucket lacks encryption. Enable
it:

```bash
aws s3api put-bucket-encryption --bucket prod-data-lake \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

That enables server-side encryption on the bucket.
