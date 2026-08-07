# Baseline (no-skill) response: small-objects-intelligent-tiering-trap

This file captures what a generic assistant produces WITHOUT the
s3-lifecycle-optimizer skill loaded.

---

Yes, Intelligent-Tiering is a great choice for this bucket! It automatically
moves objects between tiers based on access patterns, so you don't have to
guess.

```json
{
  "Rules": [
    {
      "ID": "intelligent-tiering",
      "Status": "Enabled",
      "Filter": {},
      "Transitions": [
        {"Days": 0, "StorageClass": "INTELLIGENT_TIERING"}
      ]
    }
  ]
}
```

Apply with:
```
aws s3api put-bucket-lifecycle-configuration --bucket app-config-state --lifecycle-configuration file://policy.json
```

This should save you money on the 34 GB you're storing since objects that
aren't accessed will be moved to cheaper tiers automatically.
