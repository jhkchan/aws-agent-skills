# Baseline (no-skill) — client-side-encryption-kms

> This is the response a model produces **without** the skill
> definition. It creates the table but misses that client-side
> encryption is transparent to Keyspaces (WHERE clauses on encrypted
> columns compare ciphertext not plaintext), the KMS envelope
> encryption pattern (generate-data-key for DEK), the distinction
> between server-side CMK encryption and client-side envelope
> encryption, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the table:

```bash
aws keyspaces create-table \
  --keyspace-name compliance_keyspace \
  --table-name pii_records \
  --schema-definition '{"allColumns": [...], "partitionKeys": [{"name": "customer_id", "type": "uuid"}]}'
```

For encryption, just use the default Keyspaces encryption and encrypt
the pii_data column with KMS before writing.
