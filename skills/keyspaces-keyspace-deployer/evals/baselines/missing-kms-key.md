# Baseline (no-skill) — missing-kms-key

> This is the response a model produces **without** the skill
> definition. It creates the table referencing a KMS CMK alias that
> does not exist without verifying the key exists first. The API call
> will fail at runtime. Does not emit a PREREQUISITES_MISSING verdict.
> Generated for with-skill-vs-baseline comparison.

---

Sure, here's the table:

```bash
aws keyspaces create-table \
  --keyspace-name app_keyspace \
  --table-name sensitive_data \
  --schema-definition '{"allColumns": [{"name": "id", "type": "uuid"}, {"name": "data", "type": "blob"}], "partitionKeys": [{"name": "id", "type": "uuid"}]}' \
  --encryption-spec '{"type": "CUSTOMER_MANAGED_KEYS", "kmsKeyIdentifier": "alias/nonexistent-key"}'
```

Then enable PITR and you are good.
