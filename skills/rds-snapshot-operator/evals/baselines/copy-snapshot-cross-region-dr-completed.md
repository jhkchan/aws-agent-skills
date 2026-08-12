# Baseline (no-skill) response: copy-snapshot-cross-region-dr-completed

This file captures what a generic assistant produces WITHOUT the
rds-snapshot-operator skill loaded.

---

To copy your snapshot to the DR region:

```bash
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:us-east-1:111111111111:snapshot:prod-orders-db-pre-upgrade-20260805 \
  --target-db-snapshot-identifier prod-orders-db-dr-20260805 \
  --region us-west-2
```

Since the snapshot is encrypted, you'll need to specify a KMS key in
the target region. You can check the copy status with
`describe-db-snapshots`.
