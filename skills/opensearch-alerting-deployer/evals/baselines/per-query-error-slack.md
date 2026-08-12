# Baseline (no-skill) — per-query-error-slack

> This is the response a model produces **without** the skill
> definition. It lists API calls but misses the destination-before-
> monitor ordering requirement, the per-query cost scaling concern,
> the `size: 0` optimization for aggregation-only queries, the
> severity-to-trigger relationship (severity is metadata, not routing),
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the monitor:

```bash
curl -X POST "<endpoint>/_plugins/_alerting/monitors" -d '{
  "type": "monitor",
  "name": "error-count-monitor",
  "query": { "match": { "level": "error" } }
}'
```

Then add a trigger and point it at the Slack destination.
