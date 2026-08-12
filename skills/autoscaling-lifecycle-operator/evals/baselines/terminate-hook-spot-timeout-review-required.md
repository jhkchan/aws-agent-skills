# Baseline (no-skill) response: terminate-hook-spot-timeout-review-required

This file captures what a generic assistant produces WITHOUT the
autoscaling-lifecycle-operator skill loaded.

---

To add a terminate lifecycle hook for graceful drain, use:

```bash
aws autoscaling put-lifecycle-hook \
  --lifecycle-hook-name spot-drain-hook \
  --auto-scaling-group-name prod-spot-asg \
  --lifecycle-transition autoscaling:EC2_INSTANCE_TERMINATING \
  --heartbeat-timeout 3600 \
  --default-result CONTINUE \
  --notification-target-arn arn:aws:lambda:us-east-1:111111111111:function:spot-drain-action
```

This will give your drain Lambda up to 1 hour to complete graceful
shutdown before the instance is terminated.
