# Baseline (no-skill) response: scheduled-scaling-timezone-ready

This file captures what a generic assistant produces WITHOUT the
autoscaling-policy-deployer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, timezone verification,
bounds-consistency check across overlapping scheduled actions, post-
deploy verification commands).

---

Here are the scheduled actions and target tracking:

```bash
# Target tracking
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name internal-tools-asg --policy-name cpu-target-50 \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ASGAverageCPUUtilization"},"TargetValue":50.0}'

# Scale up at 9 AM
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name internal-tools-asg \
  --scheduled-action-name business-hours-scale-up \
  --recurrence "0 9 * * Mon-Fri" \
  --min-size 4 --desired-capacity 6 --max-size 8

# Scale down at 7 PM
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name internal-tools-asg \
  --scheduled-action-name off-hours-scale-down \
  --recurrence "0 19 * * Mon-Fri" \
  --min-size 1 --desired-capacity 1 --max-size 8

# Warm pool
aws autoscaling put-warm-pool --auto-scaling-group-name internal-tools-asg --pool-state Stopped --min-size 1
```

This will scale the ASG up for business hours and down for off-hours.
