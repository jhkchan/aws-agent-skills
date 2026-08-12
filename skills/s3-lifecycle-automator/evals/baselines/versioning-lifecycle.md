# Baseline (no-skill) response: versioning-lifecycle

This file captures what a generic assistant produces WITHOUT the
s3-lifecycle-automator skill loaded.

---

For versioned buckets, you can set up lifecycle rules that handle both
current and non-current versions. Use NoncurrentVersionTransition to
move old versions to cheaper storage and NoncurrentVersionExpiration to
delete them eventually.

The lifecycle configuration would include transitions for current
versions and separate rules for non-current versions. You can also set
up abort for incomplete multipart uploads.

```
aws s3api put-bucket-lifecycle-configuration --bucket versioned-data-bucket ...
```

I'm not sure about all the field names for the non-current version
rules. You might need to look up the API reference for the exact JSON
structure.
