# Baseline (no-skill) — global-datastore-cross-region

> This is the response a model produces **without** the skill definition.
> It lists Global Datastore commands but misses the prerequisite that
> the primary cluster must be cluster-mode-enabled, that each region
> needs its own CMK, the AUTH-without-TLS anti-pattern, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to set up a cross-region Redis:

1. Create clusters in each region:
```bash
aws elasticache create-replication-group \
  --replication-group-id prod-geo-cache-us-east-1 \
  --engine redis \
  --cache-node-type cache.r6g.2xlarge \
  --num-cache-clusters 2

aws elasticache create-replication-group \
  --replication-group-id prod-geo-cache-eu-west-1 \
  --engine redis \
  --cache-node-type cache.r6g.2xlarge \
  --num-cache-clusters 2 \
  --region eu-west-1
```

2. Link them with Global Datastore:
```bash
aws elasticache create-global-replication-group \
  --global-replication-group-id-suffix prod-geo-cache \
  --primary-replication-group-id prod-geo-cache-us-east-1
```

That should give you cross-region replication.
