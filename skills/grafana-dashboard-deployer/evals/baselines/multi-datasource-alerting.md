# Baseline (no-skill) — multi-datasource-alerting

> This is the response a model produces **without** the skill definition.
> It creates a workspace with multiple data sources but misses the IAM role
> scoping per data source type, the notification policy + contact point
> chain (rules fire but go nowhere), and the 3-tier dashboard layout pattern.

---

To create a multi-source Grafana workspace:

1. Create workspace with all data sources:
```bash
aws grafana create-workspace \
  --workspace-name fullstack-obs \
  --authentication-providers AWS_SSO \
  --permission-type SERVICE_MANAGED \
  --data-sources CLOUDWATCH PROMETHEUS XRAY
```

2. Add each data source in the Grafana UI.

3. Create alert rules for your metrics.

4. Configure notifications.
