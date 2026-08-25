# DocumentDB Cluster Deployer — error handling (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Error handling (moved from SKILL.md)


### Cluster stuck in STORAGE_FULL
- Storage has hit the autoscaling ceiling. Increase the ceiling with
  `modify-db-cluster` or delete data. All writes are rejected until free
  space is available.

### Queries are slow (seconds of latency)
- Missing indexes. DocumentDB has no query optimizer. Connect via mongo
  shell, run `db.collection.getIndexes()` to verify. Create indexes
  before redeploying the application queries.

### Change stream not emitting events
- `change_streams_log_retention_duration` is 0 in the parameter group.
  Set it to 172800 (2 days) and reboot the cluster.

### Connection failures (TLS handshake error)
- TLS is enabled but the client is not using the CA bundle. Download
  `rds-combined-ca-bundle.pem` and pass it via `--tlsCAFile`.

### Replica lag is high
- Check if the primary is overloaded (CPU, memory). Consider scaling up
  the instance class or adding replicas.

