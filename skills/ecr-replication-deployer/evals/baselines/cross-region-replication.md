# Baseline (no-skill) — cross-region-replication

> This is the response a model produces **without** the skill
> definition. It configures replication but misses that replication
> is at the registry level (ALL repos replicate, not per-repo),
> that replicated images are read-only in the destination, that
> storage cost triples across three regions, the replication lag
> awareness requirement, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Configure cross-region replication:

```bash
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [{
      "destinations": [
        {"region": "us-west-2", "registryId": "111122223333"},
        {"region": "eu-west-1", "registryId": "111122223333"}
      ]
    }]
  }'
```

That should cover DR.
