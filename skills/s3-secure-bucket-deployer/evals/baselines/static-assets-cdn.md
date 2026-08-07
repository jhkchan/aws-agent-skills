# Baseline (no-skill) — static-assets-cdn

> This is the response a model produces **without** the skill definition.
> It gives basic create commands but misses BPA, BucketOwnerEnforced, the
> HTTPS enforcement policy, and the workload-specific guidance for CDN
> origins (no lifecycle needed, versioning optional).

---

Here's how to create your CDN bucket:

```bash
aws s3api create-bucket --bucket cdn-assets-prod --region us-east-1

aws s3api put-bucket-encryption --bucket cdn-assets-prod \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws s3api put-bucket-logging --bucket cdn-assets-prod \
  --bucket-logging-status '{"LoggingEnabled":{"TargetBucket":"s3-access-logs-prod","TargetPrefix":"cdn/"}}'
```

Since this is a CDN bucket, you might want to set up a CloudFront
distribution in front of it. You can use an Origin Access Identity (OAI)
or Origin Access Control (OAC) to restrict access so only CloudFront can
read from the bucket.

Don't forget to enable Block Public Access since this bucket shouldn't
be directly public.
