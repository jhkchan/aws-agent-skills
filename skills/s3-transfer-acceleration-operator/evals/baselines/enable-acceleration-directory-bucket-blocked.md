# Baseline (no-skill) response: enable-acceleration-directory-bucket-blocked

This file captures what a generic assistant produces WITHOUT the
s3-transfer-acceleration-operator skill loaded.

---

To enable Transfer Acceleration on your S3 bucket, run:

```bash
aws s3api put-bucket-accelerate-configuration \
  --bucket my-express-bucket--xaz-use1-az1 \
  --accelerate-configuration Status=Enabled
```

This will enable the accelerate endpoint for your bucket.
