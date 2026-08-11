# Baseline (no-skill) response: enable-acceleration-standard-bucket-ready

This file captures what a generic assistant produces WITHOUT the
s3-transfer-acceleration-operator skill loaded.

---

To enable Transfer Acceleration on your S3 bucket, run:

```bash
aws s3api put-bucket-accelerate-configuration \
  --bucket prod-data-lake \
  --accelerate-configuration Status=Enabled
```

You can then use the accelerate endpoint:
`prod-data-lake.s3-accelerate.amazonaws.com` for faster uploads.
