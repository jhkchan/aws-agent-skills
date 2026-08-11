# Baseline (no-skill) response: disable-acceleration-inflight-blocked

This file captures what a generic assistant produces WITHOUT the
s3-transfer-acceleration-operator skill loaded.

---

To disable Transfer Acceleration on your bucket, run:

```bash
aws s3api put-bucket-accelerate-configuration \
  --bucket prod-data-lake \
  --accelerate-configuration Status=Suspended
```

This will disable the accelerate endpoint for your bucket.
