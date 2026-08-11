# Baseline (no-skill) — table-target-tracking

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the SLR role check,
> the correct predefined metric names, the Min/Max capacity envelope
> importance, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Here's how to set up DynamoDB auto-scaling:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/orders-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 10 --max-capacity 40000

aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/orders-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-name orders-read \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70}'
```

Repeat for write capacity. That should work.
