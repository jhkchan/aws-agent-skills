# Baseline (no-skill) response: target-tracking-cpu-ready

This file captures what a generic assistant produces WITHOUT the
autoscaling-policy-deployer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, prerequisite verification,
silent-failure awareness, post-deploy verification commands).

---

Here's the target tracking policy for your ASG:

```bash
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name prod-web-asg \
  --policy-name cpu-target-50 \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ASGAverageCPUUtilization"},"TargetValue":50.0}'
```

This will scale your ASG to maintain 50% CPU utilization. The cooldown
and scaling adjustments are handled automatically by target tracking.

You can verify with:
```bash
aws autoscaling describe-policies --auto-scaling-group-names prod-web-asg
```
