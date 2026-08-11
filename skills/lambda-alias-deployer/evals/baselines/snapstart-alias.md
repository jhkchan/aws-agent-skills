# Baseline (no-skill) — snapstart-alias

> This is the response a model produces **without** the skill
> definition. It creates the alias without enabling SnapStart first
> (so the version does not get a snapshot), does not explain the
> publish-after-enable ordering, and does not emit the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

To create a staging alias:

```bash
aws lambda create-alias \
  --function-name my-function \
  --name staging \
  --function-version 1
```

You can enable SnapStart later if needed.
