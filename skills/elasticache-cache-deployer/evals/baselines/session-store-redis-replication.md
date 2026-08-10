# Baseline (no-skill) — session-store-redis-replication

> This is the response a model produces **without** the skill definition.
> It misses the noeviction-vs-allkeys-lru distinction (sessions must
> NOT be silently evicted), the cluster-mode-disabled + Multi-AZ
> topology rationale, the AUTH-without-TLS anti-pattern, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to set up a Redis session store:

```bash
aws elasticache create-replication-group \
  --replication-group-id prod-sessions \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --auth-token "myPassword123"
```

Sessions will be cached. Add a snapshot window if you want backups.

```bash
aws elasticache modify-replication-group \
  --replication-group-id prod-sessions \
  --snapshot-retention-limit 7
```
