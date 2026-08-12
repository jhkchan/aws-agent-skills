# Baseline (no-skill) response: min-days-validation-fail

This file captures what a generic assistant produces WITHOUT the
s3-lifecycle-automator skill loaded.

---

To get the fastest possible transition to cheap storage, you can set
the lifecycle policy to transition to IA at 15 days and Glacier IR at
60 days. This will move objects to cheaper storage sooner and save costs.

```
aws s3api put-bucket-lifecycle-configuration --bucket cost-optimization-target --lifecycle-configuration '{"Rules":[{"Transitions":[{"Days":15,"StorageClass":"STANDARD_IA"},{"Days":60,"StorageClass":"GLACIER_IR"}]}]}'
```

This should start transitioning objects quickly. Deploy it and monitor
your S3 costs to verify the savings.
