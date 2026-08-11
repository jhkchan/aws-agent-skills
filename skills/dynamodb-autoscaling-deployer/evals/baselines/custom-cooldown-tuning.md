# Baseline (no-skill) — custom-cooldown-tuning

> This is the response a model produces **without** the skill
> definition. It uses the default target utilization (70%) instead
> of the operator's requested 50%, omits cooldown configuration,
> forgets the throttle alarm, and skips the READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

To set up auto-scaling for your events table:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/events-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 20 --max-capacity 30000

aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/events-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-name events-read \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70}'
```

The defaults should handle spiky workloads fine.
