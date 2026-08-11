# Baseline (no-skill) response: archive-tiers-not-configured

This file captures what a generic assistant produces WITHOUT the
s3-intelligent-tiering-optimizer skill loaded.

---

Your `data-lake-curated` bucket already has Intelligent-Tiering enabled,
which is good. The objects in the Infrequent Access tier are already
being optimised by AWS.

If you want to add archive tiers, you can update the configuration:

```bash
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket data-lake-curated \
  --intelligent-tiering-configuration file://config.json
```

```json
{
  "Id": "Config",
  "Status": "Enabled",
  "Tierings": [
    {"AccessTier": "ARCHIVE_ACCESS", "Days": 90},
    {"AccessTier": "DEEP_ARCHIVE_ACCESS", "Days": 180}
  ]
}
```

This should help with the older objects that aren't being accessed.
