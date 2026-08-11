# Baseline (no-skill) — on-demand-keyspace-table-pitr

> This is the response a model produces **without** the skill
> definition. It creates the keyspace and table but misses that PITR is
> DISABLED by default in Keyspaces (unlike what many assume), the CMK
> encryption specification format, the VPC endpoint private DNS
> requirement for the Cassandra driver, the composite partition key
> cardinality analysis, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the keyspace:

```bash
aws keyspaces create-keyspace --keyspace-name event_store
```

Create the table:

```bash
aws keyspaces create-table \
  --keyspace-name event_store \
  --table-name user_events \
  --schema-definition '{"allColumns": [{"name": "user_id", "type": "uuid"}, ...], "partitionKeys": [{"name": "user_id", "type": "uuid"}]}'
```

PITR should be on by default. Connect with the Cassandra driver on port 9042.
