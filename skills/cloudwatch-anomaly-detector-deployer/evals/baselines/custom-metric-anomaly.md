# Baseline (no-skill) — custom-metric-anomaly

> This is the response a model produces **without** the skill
> definition. It creates the detector on the custom metric but misses
> the p99 stat specificity, the std dev 2 rationale (latency
> volatility), the band-breach alarm using metric math, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the anomaly detector for your custom metric:

```bash
aws cloudwatch put-metric-anomaly-detector \
  --namespace "MyApp" \
  --metric-name "RequestLatency" \
  --dimensions Name=ServiceName,Value=checkout-service \
  --stat "Average" \
  --period 60
```

Then set up an alarm on it.
