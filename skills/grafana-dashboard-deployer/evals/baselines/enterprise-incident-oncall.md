# Baseline (no-skill) — enterprise-incident-oncall

> This is the response a model produces **without** the skill definition.
> It creates a Standard workspace instead of Enterprise, misses the SAML
> team sync configuration, the Incident and OnCall feature enablement, and
> the 5-data-source IAM role scoping.

---

To create a Grafana workspace for enterprise:

1. Create the workspace:
```bash
aws grafana create-workspace \
  --workspace-name enterprise-obs \
  --authentication-providers AWS_SSO \
  --permission-type SERVICE_MANAGED \
  --data-sources CLOUDWATCH PROMETHEUS TIMESTREAM OPENSEARCH XRAY
```

2. Configure SAML authentication in the UI.

3. Enable Incident and OnCall plugins.

4. Create dashboards and alerts.
