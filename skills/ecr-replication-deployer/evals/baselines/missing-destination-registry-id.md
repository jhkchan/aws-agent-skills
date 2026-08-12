# Baseline (no-skill) — missing-destination-registry-id

> This is the response a model produces **without** the skill
> definition. It attempts to configure cross-account replication
> without knowing the destination account's registry ID, guessing
> or leaving a placeholder, which would fail silently. Does not
> emit a PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Configure cross-account replication:

```bash
aws ecr put-registry-replication-configuration \
  --replication-configuration '{
    "rules": [{
      "destinations": [
        {"region": "us-east-1", "registryId": "TODO_FILL_IN"}
      ]
    }]
  }'
```

Just replace the registry ID when you find it.
