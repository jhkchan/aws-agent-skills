# Baseline (no-skill) response: warm-pool-fast-scale-out-completed

This file captures what a generic assistant produces WITHOUT the
autoscaling-lifecycle-operator skill loaded.

---

To configure a warm pool, use:

```bash
aws autoscaling put-warm-pool \
  --auto-scaling-group-name prod-web-asg \
  --pool-min-size 3 \
  --max-group-prepared-capacity 5
```

This will keep 3 pre-booted instances ready for fast scale-out.
Verify with `aws autoscaling describe-warm-pool`.
