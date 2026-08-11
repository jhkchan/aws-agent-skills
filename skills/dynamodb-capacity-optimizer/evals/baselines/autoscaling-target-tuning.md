# Baseline (no-skill) response: autoscaling-target-tuning

This file captures what a generic assistant produces WITHOUT the
dynamodb-capacity-optimizer skill loaded.

---

Your table is experiencing throttling with 145,000 throttled read
requests. Your auto-scaling target is set to 90%, which is quite high.
When traffic spikes, the capacity gets exhausted before auto-scaling
can react.

You should lower the auto-scaling target to something like 70% or 60%
and increase the max capacity so it has room to scale up:

```
aws application-autoscaling put-scaling-policy \
  --policy-name tbl-autoscaling-target-tuning-read \
  --service-namespace dynamodb \
  --target-tracking-scaling-policy-configuration '{"TargetValue": 60.0}'
```

This should give more headroom and reduce throttling during spikes.
