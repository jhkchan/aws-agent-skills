# Baseline (no-skill) response: glacier-instant-retrieval-no-restore-blocked

This file captures what a generic assistant produces WITHOUT the
s3-glacier-restore-operator skill loaded.

---

To restore the Glacier Instant Retrieval object:

```bash
aws s3api restore-object \
  --bucket warm-archive-bucket \
  --key user-events-2025-07.parquet \
  --restore-request '{"Days": 7, "GlacierJobParameters": {"Tier": "Expedited"}}'
```

After 1-5 minutes, read the object with `aws s3api get-object`.
