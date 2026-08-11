# Baseline (no-skill) — postgresql-source-cdc-secrets-manager

> This is the response a model produces **without** the skill
> definition. It creates the endpoint but misses the CDC prerequisite
> check (wal_level=logical), the Secrets Manager integration pattern,
> the extra connection attributes (PluginName=pglogical), and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

To create a DMS PostgreSQL source endpoint:

1. Go to DMS console and create a source endpoint.
2. Select PostgreSQL and enter the server, port, and database.
3. Enter username and password.
4. Test the connection.

```bash
aws dms create-endpoint --engine-name postgres --server-name prod-db \
  --port 5432 --database-name analytics --username dms_user
```

You can enable CDC in the replication task settings.
