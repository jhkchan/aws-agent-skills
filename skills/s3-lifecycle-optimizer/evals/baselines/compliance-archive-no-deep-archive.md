# Baseline (no-skill) response: compliance-archive-no-deep-archive

This file captures what a generic assistant produces WITHOUT the
s3-lifecycle-optimizer skill loaded.

---

For your compliance archive bucket, you could move objects to Glacier to save
money since they're rarely accessed.

```json
{
  "Rules": [
    {
      "ID": "archive",
      "Status": "Enabled",
      "Filter": {},
      "Transitions": [
        {"Days": 30, "StorageClass": "GLACIER"}
      ]
    }
  ]
}
```

The 7-year retention requirement should be fine as long as you don't delete
anything early. Make sure to also enable Object Lock if you need compliance
guarantees.

You can use `aws s3api put-bucket-lifecycle-configuration` to apply this.
