# Baseline (no-skill) — provisioned-concurrency-alias

> This is the response a model produces **without** the skill
> definition. It puts provisioned concurrency on the version
> number instead of the alias, does not configure Auto Scaling,
> and does not emit the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

To set up provisioned concurrency:

```bash
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier 5 \
  --provisioned-concurrent-executions 10
```

That should eliminate cold starts.
