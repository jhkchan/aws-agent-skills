# Baseline (no-skill) — missing-deployment-strategy

> This is the response a model produces **without** the skill
> definition. It attempts to deploy without a deployment strategy,
> does not flag the missing prerequisite, and does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-
> baseline comparison.

---

Here's the deployment:

```bash
aws appconfig start-deployment \
  --application-id abc12345 \
  --environment-id def67890 \
  --configuration-profile-id ghi11111
```

That should work.
