# Baseline (no-skill) — missing-published-version

> This is the response a model produces **without** the skill
> definition. It attempts to create the alias pointing to $LATEST
> without checking for published versions, and does not emit the
> READY_TO_DEPLOY or PREREQUISITES_MISSING checklist format.
> Generated for with-skill-vs-baseline comparison.

---

To create a prod alias:

```bash
aws lambda create-alias \
  --function-name my-function \
  --name prod \
  --function-version '$LATEST'
```

The alias will point to the latest code.
