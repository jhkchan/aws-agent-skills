# Baseline (no-skill) response: intelligent-tiering-optin

This file captures what a generic assistant produces WITHOUT the
s3-lifecycle-automator skill loaded.

---

Intelligent-Tiering is a good choice for data with unpredictable access
patterns. You can enable it by creating a lifecycle rule that transitions
objects to the INTELLIGENT_TIERING storage class.

```
aws s3api put-bucket-lifecycle-configuration --bucket data-lake-raw --lifecycle-configuration '{"Rules":[{"Transitions":[{"Days":0,"StorageClass":"INTELLIGENT_TIERING"}]}]}'
```

There might also be a separate configuration for archive tiers. Check
the S3 docs for the Intelligent-Tiering archive configuration options.
