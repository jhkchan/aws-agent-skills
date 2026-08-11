# Baseline (no-skill) — exponential-with-validators-and-feature-flags

> This is the response a model produces **without** the skill
> definition. It lists basic commands but misses the feature flag
> schema requirement (feature flags need a specific schema URI,
> not just a JSON profile), the exponential growth type parameter,
> the JSON schema validation attachment, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Here's the AppConfig setup:

```bash
aws appconfig create-configuration-profile \
  --application-id abc12345 \
  --name feature-flag-store \
  --type AWS.Freeform
```

Then deploy with exponential strategy.
