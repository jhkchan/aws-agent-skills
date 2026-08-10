# Baseline (no-skill) — missing-subnet-group-and-sg

> This is the response a model produces **without** the skill definition.
> It blindly issues a create-replication-group command without
> flagging the missing subnet group (Multi-AZ requires a multi-AZ
> subnet group), the missing security group (cache port inbound),
> or the missing AUTH token details (AUTH requires TLS) — exactly
> the prerequisites the skill is designed to catch. Generated for
> with-skill-vs-baseline comparison.

---

Here's how to create your Redis cache:

```bash
aws elasticache create-replication-group \
  --replication-group-id orders-cache \
  --engine redis \
  --cache-node-type cache.r6g.large \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --auth-token "myPassword123"
```

That should give you a Multi-AZ Redis with AUTH. Let me know if you
need anything else.
