# Baseline (no-skill) — amp-prometheus-dashboard

> This is the response a model produces **without** the skill definition.
> It creates a workspace with AMP data source but misses the customer-managed
> IAM role with aps:QueryMetrics permission, AMP workspace status verification,
> and the PromQL dashboard + alerting configuration.

---

To create a Grafana workspace with AMP:

1. Create the workspace:
```bash
aws grafana create-workspace \
  --workspace-name app-monitoring \
  --authentication-providers AWS_SSO \
  --permission-type SERVICE_MANAGED \
  --data-sources PROMETHEUS
```

2. Add the AMP workspace as a Prometheus data source in the Grafana UI.

3. Create PromQL dashboards.
