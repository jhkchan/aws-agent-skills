# Baseline (no-skill) — missing-prerequisites

> This is the response a model produces **without** the skill
> definition. It blindly emits auto-scaling commands without
> verifying that the table exists, its billing mode, or the
> application auto-scaling SLR — all of which will fail at runtime.
> Generated for with-skill-vs-baseline comparison.

---

Here's how to set up the scaling:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/non-existent-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 --max-capacity 10000

aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/non-existent-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-name read-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70}'
```

That should set it up.
