# Baseline (no-skill) — all-at-once-json-config

> This is the response a model produces **without** the skill
> definition. It creates the deployment but does not flag the risk
> of all-at-once with 0-minute bake (no alarm monitoring), does not
> emit a READY_TO_DEPLOY checklist, and does not note the
> configuration profile type immutability. Generated for with-skill-
> vs-baseline comparison.

---

Create the config and deploy:

```bash
aws appconfig create-application --name simple-config-app
aws appconfig start-deployment --application-id abc12345
```

Done.
