# Baseline (no-skill) response: predictable-access-lifecycle-cheaper

This file captures what a generic assistant produces WITHOUT the
s3-intelligent-tiering-optimizer skill loaded.

---

Yes, you could enable Intelligent-Tiering on `media-thumbnails` to
save cost. It will automatically move objects that aren't accessed to
cheaper tiers.

```bash
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket media-thumbnails \
  --intelligent-tiering-configuration file://config.json
```

```json
{
  "Id": "Config",
  "Status": "Enabled",
  "Tierings": [
    {"AccessTier": "ARCHIVE_ACCESS", "Days": 90}
  ]
}
```

Since your thumbnails are served via a CDN, the ones that aren't
accessed frequently will automatically move to cheaper storage.
