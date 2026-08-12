# Baseline (no-skill) — entitlement-cross-account

> This is the response a model produces **without** the skill
> definition. It attempts to share via IAM bucket policy (entitlements
> are the sharing mechanism, NOT IAM), misses the receiving account's
> need for its own Data Exchange subscription/entitlement, and lacks
> the READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Share the bucket with the other account using a bucket policy:

```bash
aws s3api put-bucket-policy \
  --bucket my-data-bucket \
  --policy '{
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::999999999999:root"},
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-data-bucket/*"
    }]
  }'
```

The other account can now access the data.
