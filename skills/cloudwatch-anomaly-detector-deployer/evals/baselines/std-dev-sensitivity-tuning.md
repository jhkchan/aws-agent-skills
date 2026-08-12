# Baseline (no-skill) — std-dev-sensitivity-tuning

> This is the response a model produces **without** the skill
> definition. It creates the detector but uses the default std dev 3
> (missing the operator's request for std dev 2 for volatile latency),
> misses the composite alarm integration combining anomaly AND static
> threshold, and omits the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Set up anomaly detection for your ALB latency:

```bash
aws cloudwatch put-metric-anomaly-detector \
  --namespace "AWS/ApplicationELB" \
  --metric-name "TargetResponseTime" \
  --dimensions Name=LoadBalancer,Value=app/prod-alb/1234567890 \
  --stat "Average" \
  --period 60
```

Then create an alarm on it.
