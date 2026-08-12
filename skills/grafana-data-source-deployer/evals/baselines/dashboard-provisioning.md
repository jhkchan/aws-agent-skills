# Baseline (no-skill) — dashboard-provisioning

> This is the response a model produces **without** the skill
> definition. It creates an API key but misses the data source UID
> verification (mismatched UIDs cause panels to show "No data"
> silently), the API key one-time-display warning (must be stored
> immediately), and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Create an API key and import dashboards:

```bash
aws grafana create-workspace-api-key \
  --workspace-id g-aaaa1111 \
  --key-name ci-cd-provisioning \
  --key-role ADMIN \
  --seconds-to-live 86400
```

Then use the Grafana API to import your dashboard JSON files.
