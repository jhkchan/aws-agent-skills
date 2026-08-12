# Baseline (no-skill) — multi-region-dr-with-lifecycle

> This is the response a model produces **without** the skill
> definition. It configures replication but misses that lifecycle
> policies must be applied independently in EACH region (source and
> both destinations — they do not propagate), that storage cost
> triples across three regions, the replication lag for large 2-5GB
> images, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Configure replication:

```bash
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [{
      "destinations": [
        {"region": "us-west-2", "registryId": "111122223333"},
        {"region": "ap-southeast-2", "registryId": "111122223333"}
      ]
    }]
  }'
```

Then apply a lifecycle policy:

```bash
aws ecr put-lifecycle-policy --repository-name my-app \
  --lifecycle-policy-text file://policy.json
```
