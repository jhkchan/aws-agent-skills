# Baseline (no-skill) — on-demand-vs-provisioned

> This is the response a model produces **without** the skill
> definition. It blindly attempts to register scalable targets on an
> on-demand table without advising the mode switch, which will fail
> at runtime. Generated for with-skill-vs-baseline comparison.

---

Here's how to set up auto-scaling on your table:

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/users-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 5 --max-capacity 10000

aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/users-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-name users-read \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70}'
```

That should do it.
