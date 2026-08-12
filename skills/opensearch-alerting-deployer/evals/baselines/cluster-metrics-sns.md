# Baseline (no-skill) — cluster-metrics-sns

> This is the response a model produces **without** the skill
> definition. It creates the monitor but misses the notification plugin
> (notification.yaml) requirement for SNS actions, the cluster metrics
> monitor type distinction, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the monitor to check JVM heap and notify SNS:

```bash
curl -X POST "<endpoint>/_plugins/_alerting/monitors" -d '{
  "type": "monitor",
  "name": "jvm-heap-monitor",
  "actions": [{ "destination_id": "<sns-dest>", "sns_topic_arn": "..." }]
}'
```
