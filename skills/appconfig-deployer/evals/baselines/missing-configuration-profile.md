# Baseline (no-skill) — missing-configuration-profile

> This is the response a model produces **without** the skill
> definition. It attempts to deploy without a configuration profile
> or version, does not flag the missing prerequisite, and does not
> emit a PREREQUISITES_MISSING verdict. Generated for with-skill-vs-
> baseline comparison.

---

Start the deployment:

```bash
aws appconfig start-deployment \
  --application-id abc12345 \
  --environment-id def67890 \
  --deployment-strategy-id jkl22222
```

Should be fine.
