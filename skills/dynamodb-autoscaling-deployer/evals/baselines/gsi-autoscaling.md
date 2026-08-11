# Baseline (no-skill) — gsi-autoscaling

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the correct GSI
> resource-id format (table/<name>/index/<gsi>), uses the wrong
> scalable-dimension (table: instead of index:), and omits the
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

For GSI auto-scaling, run something like:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/orders-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 --max-capacity 20000

aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/orders-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-name gsi-read \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70}'
```

That should set it up.
