# Baseline (no-skill) — cloudwatch-data-source

> This is the response a model produces **without** the skill
> definition. It creates the workspace but misses the workspace IAM
> role with per-service CloudWatch permissions (cloudwatch:GetMetricData,
> logs:StartQuery), the data source configuration via Grafana API, the
> workspace status check (ACTIVE before configuring), and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the Grafana workspace:

```bash
aws grafana create-workspace \
  --workspace-name prod-observability \
  --account-access-type CURRENT_ACCOUNT \
  --authentication-provider AWS_SSO \
  --data-sources CLOUDWATCH
```

That should give you a Grafana workspace with CloudWatch.
