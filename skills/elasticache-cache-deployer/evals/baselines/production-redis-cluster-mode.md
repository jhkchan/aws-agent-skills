# Baseline (no-skill) — production-redis-cluster-mode

> This is the response a model produces **without** the skill definition.
> It lists CLI commands but misses the cluster-mode shard rationale,
> the AUTH-without-TLS anti-pattern, the 50% memory rule for Redis,
> the subnet-group-must-span-2-AZs Multi-AZ requirement, the
> allkeys-lru maxmemory-policy decision, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Here's how to create a Redis cache:

1. Create the cluster:
```bash
aws elasticache create-replication-group \
  --replication-group-id prod-cache \
  --engine redis \
  --cache-node-type cache.r6g.2xlarge \
  --num-cache-clusters 2 \
  --automatic-failover-enabled
```

2. Add encryption:
```bash
aws elasticache modify-replication-group \
  --replication-group-id prod-cache \
  --at-rest-encryption-enabled \
  --auth-token "myPassword123"
```

3. Enable snapshots:
```bash
aws elasticache modify-replication-group \
  --replication-group-id prod-cache \
  --snapshot-retention-limit 7
```

That should cover it.
