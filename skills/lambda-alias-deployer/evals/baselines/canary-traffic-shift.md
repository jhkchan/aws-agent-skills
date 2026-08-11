# Baseline (no-skill) — canary-traffic-shift

> This is the response a model produces **without** the skill
> definition. It suggests updating the function code instead of
> using weighted alias routing, does not explain the progressive
> shift lifecycle, does not mention rollback, and does not emit
> the READY_TO_DEPLOY checklist format. Generated for with-skill-
> vs-baseline comparison.

---

To deploy version 6 gradually:

1. Update the alias to point to version 6:
```bash
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 6
```

2. Monitor for errors, then keep it if it works.

That should deploy the new version.
