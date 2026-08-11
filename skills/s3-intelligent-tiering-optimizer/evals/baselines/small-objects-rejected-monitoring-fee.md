# Baseline (no-skill) response: small-objects-rejected-monitoring-fee

This file captures what a generic assistant produces WITHOUT the
s3-intelligent-tiering-optimizer skill loaded.

---

Yes, you should move your `app-config-state` bucket to
Intelligent-Tiering. It will automatically move objects that aren't
accessed to cheaper tiers.

```bash
aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket app-config-state \
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

The monitoring fee is small — $0.0025 per 1,000 objects. For your 8.2
million objects that's about $20/month, which is worth it for the
automatic optimisation.
