# Baseline (no-skill) response: versioning-bloat

This file captures what a generic assistant produces WITHOUT the
s3-storage-class-optimizer skill loaded.

---

Your bucket has 50 TB total with 12 TB of noncurrent versions. That's
a lot of wasted storage. You should add lifecycle rules to clean up
old versions.

You can add a lifecycle rule to expire noncurrent versions:

```
aws s3api put-bucket-lifecycle-configuration \
  --bucket bucket-versioning-bloat \
  --lifecycle-configuration file://lifecycle.json
```

You might also want to clean up the incomplete multipart uploads
which are using 2 TB. You should also consider whether you need
versioning enabled at all.
