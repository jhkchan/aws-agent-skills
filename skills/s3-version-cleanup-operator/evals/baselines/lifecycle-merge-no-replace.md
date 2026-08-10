# Baseline (no-skill) response: lifecycle-merge-no-replace

This file captures what a generic assistant produces WITHOUT the
s3-version-cleanup-operator skill loaded.

---

You can add a NoncurrentVersionExpiration rule to your bucket with:

```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket prod-logs-bucket \
  --lifecycle-configuration '{
    "Rules": [{
      "ID": "version-cleanup-3-rule",
      "Status": "Enabled",
      "Filter": {"Prefix": ""},
      "NoncurrentVersionExpiration": {
        "NewerNoncurrentVersions": 3
      }
    }]
  }'
```

This will keep only the 3 most recent noncurrent versions and expire
the rest. Wait 24-48 hours for the cleanup to take effect.
