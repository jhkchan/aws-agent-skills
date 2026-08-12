# Baseline (no-skill) — per-document-monitor

> This is the response a model produces **without** the skill
> definition. It creates a monitor but misses the per-document monitor
> type distinction (uses the wrong type), the per-row action semantics
> (one action per matching document), and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the monitor:

```bash
curl -X POST "<endpoint>/_plugins/_alerting/monitors" -d '{
  "type": "monitor",
  "name": "per-user-error-monitor",
  "query": { "match": { "level": "error" } }
}'
```

Add a trigger that fires on each error.
