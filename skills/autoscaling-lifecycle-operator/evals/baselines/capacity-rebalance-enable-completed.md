# Baseline (no-skill) response: capacity-rebalance-enable-completed

This file captures what a generic assistant produces WITHOUT the
autoscaling-lifecycle-operator skill loaded.

---

To enable capacity rebalance on your Spot ASG, use:

```bash
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name prod-spot-asg \
  --capacity-rebalance
```

This will allow the ASG to proactively replace Spot instances when a
rebalance recommendation is received. Verify with
`aws autoscaling describe-auto-scaling-groups`.
