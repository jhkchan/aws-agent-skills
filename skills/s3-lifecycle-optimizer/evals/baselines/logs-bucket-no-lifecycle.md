# Baseline (no-skill) response: logs-bucket-no-lifecycle

This file captures what a generic assistant produces WITHOUT the
s3-lifecycle-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, dollar savings estimate, full
lifecycle JSON, CONFIRM gate).

---

Your bucket `app-logs-prod` is 20 TB total with 8 TB of noncurrent versions,
all in Standard storage. You should set up a lifecycle policy to move older
objects to cheaper storage and clean up noncurrent versions.

Here's a sample lifecycle policy:

```json
{
  "Rules": [
    {
      "ID": "move-to-ia",
      "Status": "Enabled",
      "Filter": {},
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"}
      ]
    }
  ]
}
```

You can apply it with:
```
aws s3api put-bucket-lifecycle-configuration --bucket app-logs-prod --lifecycle-configuration file://policy.json
```

This should save you money since IA is cheaper than Standard.

You might also want to clean up the multipart uploads.
