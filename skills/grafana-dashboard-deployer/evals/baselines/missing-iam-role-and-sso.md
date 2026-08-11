# Baseline (no-skill) — missing-iam-role-and-sso

> This is the response a model produces **without** the skill definition.
> It provides generic CLI commands without checking that IAM Identity Center
> is enabled, that an IAM role exists, or that an AMP workspace is set up,
> proceeding to deployment with placeholders instead of catching the missing
> prerequisites.

---

To create a Grafana workspace:

1. Create the workspace:
```bash
aws grafana create-workspace \
  --workspace-name team-dashboards \
  --authentication-providers AWS_SSO \
  --permission-type SERVICE_MANAGED \
  --data-sources CLOUDWATCH PROMETHEUS
```

2. Set up CloudWatch and AMP data sources.

3. Create dashboards.
