# Baseline (no-skill) — oac-sse-kms

> This is the response a model produces **without** the skill
> definition. It creates the OAC but misses that SSE-KMS requires
> the always-sign signing behavior specifically, the KMS key policy
> granting cloudfront.amazonaws.com kms:Decrypt (a separate policy
> from the S3 bucket policy), and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the OAC and attach it to the distribution. Make sure the bucket policy allows CloudFront:

```bash
aws cloudfront create-origin-access-control \
  --origin-access-control-config \
    '{"Name":"oac-kms","SigningProtocol":"sigv4","SigningBehavior":"always-sign","OriginAccessControlOriginType":"s3"}'
```

Update the S3 bucket policy to allow CloudFront access.
