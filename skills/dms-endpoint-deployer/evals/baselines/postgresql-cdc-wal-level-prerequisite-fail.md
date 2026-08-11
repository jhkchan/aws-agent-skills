# Baseline (no-skill) — postgresql-cdc-wal-level-prerequisite-fail

> This is the response a model produces **without** the skill
> definition. It attempts the PostgreSQL CDC endpoint without flagging
> the wal_level=replica prerequisite failure (CDC requires
> wal_level=logical), missing the source-database prerequisite check
> entirely. Generated for with-skill-vs-baseline comparison.

---

To create a DMS PostgreSQL CDC source endpoint:

1. Create the endpoint for PostgreSQL.
2. Enable the pglogical plugin.
3. Create the replication task with CDC.

```bash
aws dms create-endpoint --engine-name postgres --server-name staging-db \
  --port 5432 --database-name staging
```

CDC should work with the pglogical plugin.
