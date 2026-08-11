# Baseline (no-skill) — export-s3-compliance

> This is the response a model produces **without** the skill
> definition. It creates the ledger and mentions S3 export but does not
> detail the IAM role requirements (S3 write permissions + QLDB trust),
> does not explain the export output format (Ion blocks), does not note
> the async nature of exports, and omits the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the ledger:

```bash
aws qldb create-ledger \
  --name regulatory-ledger \
  --permissions-mode STANDARD \
  --deletion-protection \
  --region us-east-1
```

Then export to S3:

```bash
aws qldb export-journal-to-s3 \
  --name regulatory-ledger \
  --role-arn arn:aws:iam::123456789012:role/QLDBExportRole \
  --output-s3-prefix s3://qldb-regulatory-export/ \
  --start-time 2026-01-01T00:00:00Z \
  --end-time 2026-12-31T23:59:59Z
```

The export will appear in S3.
