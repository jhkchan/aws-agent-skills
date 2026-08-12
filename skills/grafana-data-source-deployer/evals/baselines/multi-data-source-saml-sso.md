# Baseline (no-skill) — multi-data-source-saml-sso

> This is the response a model produces **without** the skill
> definition. It creates the workspace but misses the per-service IAM
> permissions for each data source (CloudWatch, Athena, Timestream),
> the SAML IdP metadata configuration requirement, the assertion
> attribute mappings, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the Grafana workspace:

```bash
aws grafana create-workspace \
  --workspace-name enterprise-grafana \
  --authentication-provider SAML \
  --permission-type CUSTOM \
  --data-sources CLOUDWATCH ATHENA TIMESTREAM
```

Then configure SAML SSO and add the data sources.
