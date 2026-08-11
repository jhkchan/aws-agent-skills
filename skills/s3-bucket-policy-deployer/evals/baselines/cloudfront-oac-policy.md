# Baseline (no-skill) — cloudfront-oac-policy

> This is the response a model produces **without** the skill
> definition. It uses the legacy OAI canonical user ID as the
> principal (which does not support SSE-KMS and is deprecated),
> does not include the `AWS:SourceArn` condition (allowing ANY
> CloudFront distribution in the account to access the bucket),
> and omits the HTTPS-only Deny. Generated for with-skill-vs-
> baseline comparison.

---

To allow CloudFront to read from your bucket:

```bash
aws s3api put-bucket-policy \
  --bucket cdn-origin-assets \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "CanonicalUser": "c4c1ede66af53448b93e28bd014fbedd65" },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::cdn-origin-assets/*"
    }]
  }'
```

Replace the canonical user ID with your CloudFront OAI's ID from
the CloudFront console.
