# Baseline (no-skill) — missing-s3-bucket

> This is the response a model produces **without** the skill
> definition. It attempts to create the delivery stream referencing a
> nonexistent S3 bucket, which will fail at runtime (API error). The
> model does not detect the missing prerequisite proactively.
> Generated for with-skill-vs-baseline comparison.

---

Create the delivery stream:

```bash
aws firehose create-delivery-stream \
  --delivery-stream-name events-stream \
  --delivery-stream-type DirectPut \
  --s3-destination-configuration RoleARN=...,BucketARN=arn:aws:s3:::my-nonexistent-bucket
```

This will fail because the bucket does not exist.
