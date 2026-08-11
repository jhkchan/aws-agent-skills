# Baseline (no-skill) — cloudwatch-dashboard-production

> This is the response a model produces **without** the skill definition.
> It produces a generic create-workspace command but misses the customer-managed
> IAM role requirement, the CloudWatch IAM permissions, the alerting three-layer
> chain (rules + notification policies + contact points), and the READY_TO_DEPLOY
> checklist format.

---

To create a Managed Grafana workspace:

1. Create the workspace:
```bash
aws grafana create-workspace \
  --workspace-name prod-observability \
  --account-access-type CURRENT_ACCOUNT \
  --authentication-providers AWS_SSO \
  --permission-type SERVICE_MANAGED \
  --data-sources CLOUDWATCH
```

2. Log in and add CloudWatch as a data source in the Grafana UI.

3. Create a dashboard with panels for your metrics.

4. Set up alerting in the Grafana UI.
