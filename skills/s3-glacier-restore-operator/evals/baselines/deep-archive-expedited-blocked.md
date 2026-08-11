# Baseline (no-skill) response: deep-archive-expedited-blocked

This file captures what a generic assistant produces WITHOUT the
s3-glacier-restore-operator skill loaded.

---

To restore the Deep Archive object with Expedited tier:

```bash
aws s3api restore-object \
  --bucket compliance-archive \
  --key audit-2024.parquet \
  --restore-request '{"Days": 30, "GlacierJobParameters": {"Tier": "Expedited"}}'
```

Wait 1-5 minutes for the Expedited restore to complete, then use
`aws s3api get-object` to read the data.
