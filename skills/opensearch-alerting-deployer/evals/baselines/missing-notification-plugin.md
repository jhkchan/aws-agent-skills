# Baseline (no-skill) — missing-notification-plugin

> This is the response a model produces **without** the skill
> definition. It creates the monitor with an SNS action without
> flagging that the notification plugin (notification.yaml) is not
> configured on the domain. The SNS action will fail silently at
> trigger time. Does not emit a PREREQUISITES_MISSING verdict.
> Generated for with-skill-vs-baseline comparison.

---

Create the disk usage monitor with SNS:

```bash
curl -X POST "<endpoint>/_plugins/_alerting/monitors" -d '{
  "name": "disk-usage-monitor",
  "actions": [{ "destination_id": "<sns-dest>" }]
}'
```
