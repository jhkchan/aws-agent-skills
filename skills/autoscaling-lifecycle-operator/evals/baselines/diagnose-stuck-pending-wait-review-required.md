# Baseline (no-skill) response: diagnose-stuck-pending-wait-review-required

This file captures what a generic assistant produces WITHOUT the
autoscaling-lifecycle-operator skill loaded.

---

Your instance i-xxx is stuck in Pending:Wait. This means the lifecycle
hook api-bootstrap-hook is waiting for the Lambda to call
complete-lifecycle-action. Check the Lambda logs for errors. The Lambda
seems to have timed out after 30 seconds.

You can try manually completing the lifecycle action:

```bash
aws autoscaling complete-lifecycle-action \
  --lifecycle-hook-name api-bootstrap-hook \
  --auto-scaling-group-name prod-api-asg \
  --lifecycle-action-result CONTINUE
```

You may also want to increase the Lambda timeout.
