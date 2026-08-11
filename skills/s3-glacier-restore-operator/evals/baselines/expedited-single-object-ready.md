# Baseline (no-skill) response: expedited-single-object-ready

This file captures what a generic assistant produces WITHOUT the
s3-glacier-restore-operator skill loaded.

---

To restore the object from Glacier with Expedited tier:

```bash
aws s3api restore-object \
  --bucket prod-archive-bucket \
  --key quarterly-report-2025-Q1.parquet \
  --restore-request '{"Days": 7, "GlacierJobParameters": {"Tier": "Expedited"}}'
```

After a few minutes you can read the object with `aws s3api get-object`.
