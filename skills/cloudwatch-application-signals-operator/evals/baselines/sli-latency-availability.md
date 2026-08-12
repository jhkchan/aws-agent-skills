# Baseline (no-skill) — sli-latency-availability

> This is the response a model produces **without** the skill
> definition. It tries to manually create CloudWatch metrics for SLIs
> (instead of using auto-derived), does not set operation-level
> targets, omits anomaly detection, and misses the OPERATION_COMPLETED
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create CloudWatch metrics for checkout-api:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name checkout-latency \
  --namespace CheckoutAPI \
  --metric-name Latency \
  --threshold 500
```

Set availability:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name checkout-availability \
  --namespace CheckoutAPI \
  --metric-name ErrorRate \
  --threshold 0.05
```

These should track the SLIs.
