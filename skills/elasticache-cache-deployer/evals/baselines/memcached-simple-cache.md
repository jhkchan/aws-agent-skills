# Baseline (no-skill) — memcached-simple-cache

> This is the response a model produces **without** the skill definition.
> It creates a Memcached cluster but misses the explicit acknowledgment
> that Memcached has NO failover / NO persistence / NO encryption,
> the cross-az mode (distributes nodes only — NOT Multi-AZ), and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to create a Memcached cache:

```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id dev-cache \
  --engine memcached \
  --cache-node-type cache.r6g.large \
  --num-cache-nodes 3
```

Memcached is simple and should work fine for a dev cache.
