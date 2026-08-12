# Baseline (no-skill) — cross-account-replication

> This is the response a model produces **without** the skill
> definition. It configures cross-account replication but misses
> that the destination account must allow replication (not have
> REPLICATION_DISALLOWED set), that replicated images are read-only
> in the destination, that batch delete is blocked on replicas,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Configure cross-account replication:

```bash
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [{
      "destinations": [
        {"region": "us-east-1", "registryId": "999999999999"}
      ]
    }]
  }'
```

Images should replicate automatically.
