# Baseline (no-skill) — prometheus-amp-data-source

> This is the response a model produces **without** the skill
> definition. It creates the workspace but misses the aps:QueryMetrics
> permission requirement in the workspace IAM role, the SigV4
> authentication configuration for the Prometheus data source
> (sigV4Auth: true with workspace role), the AMP workspace URL format,
> and the READY_TO_DEPLOY checklist format. Generated for with-skill-
> vs-baseline comparison.

---

Create the Grafana workspace:

```bash
aws grafana create-workspace \
  --workspace-name amp-observability \
  --authentication-provider AWS_SSO \
  --data-sources PROMETHEUS
```

Then add the Prometheus data source pointing to your AMP workspace.
