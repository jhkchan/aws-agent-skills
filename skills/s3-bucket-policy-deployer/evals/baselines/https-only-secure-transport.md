# Baseline (no-skill) — https-only-secure-transport

> This is the response a model produces **without** the skill
> definition. It uses `StringNotEquals` instead of `Bool` for the
> `aws:SecureTransport` condition (the most common operator mistake),
> omits the BucketOwnerEnforced ACL disable, and does not enable
> Block Public Access. Generated for with-skill-vs-baseline
> comparison.

---

To enforce HTTPS on your S3 bucket, add this policy:

```bash
aws s3api put-bucket-policy \
  --bucket prod-app-data \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::prod-app-data/*",
      "Condition": {
        "StringNotEquals": { "aws:SecureTransport": "true" }
      }
    }]
  }'
```

This will deny any request not using HTTPS.
