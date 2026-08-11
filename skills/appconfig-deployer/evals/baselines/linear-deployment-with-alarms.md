# Baseline (no-skill) — linear-deployment-with-alarms

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the deployment
> strategy growth factor and bake time semantics (bake time =
> monitoring window for CloudWatch alarms), the Lambda validator
> lifecycle (runs BEFORE deployment, blocks on failure), and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the AppConfig deployment:

```bash
aws appconfig start-deployment \
  --application-id abc12345 \
  --environment-id def67890 \
  --configuration-profile-id ghi11111 \
  --deployment-strategy-id jkl22222
```

That should deploy the config.
