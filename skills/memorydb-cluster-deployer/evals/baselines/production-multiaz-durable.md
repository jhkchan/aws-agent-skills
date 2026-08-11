# Baseline (no-skill) — production-multiaz-durable

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the MemoryDB-vs-
> ElastiCache boundary, the TLS-on-by-default immutability, the
> named-ACL requirement (uses default open-access), the 50% memory
> rule, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Here's how to create a MemoryDB cluster:

1. Create the cluster:
```bash
aws memorydb create-cluster \
  --cluster-name prod-memorydb \
  --node-type db.r6g.24xlarge \
  --acl-name open-access
```

2. Add shards and replicas later if needed.

That should cover it.
