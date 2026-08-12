# Baseline (no-skill) — anomaly-detection-monitor

> This is the response a model produces **without** the skill
> definition. It creates a monitor referencing the anomaly detector
> but misses the RCF cold start consideration, the detector state
> verification requirement, the anomaly_grade threshold semantics,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the anomaly detection monitor:

```bash
curl -X POST "<endpoint>/_plugins/_alerting/monitors" -d '{
  "name": "latency-anomaly-monitor",
  "anomaly_detector": { "detector_id": "latency-detector-001" }
}'
```

Then add a trigger for anomaly grade.
