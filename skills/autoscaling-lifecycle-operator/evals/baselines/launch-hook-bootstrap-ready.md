# Baseline (no-skill) response: launch-hook-bootstrap-ready

This file captures what a generic assistant produces WITHOUT the
autoscaling-lifecycle-operator skill loaded.

---

To add a launch lifecycle hook, use the following command:

```bash
aws autoscaling put-lifecycle-hook \
  --lifecycle-hook-name web-bootstrap-hook \
  --auto-scaling-group-name prod-web-asg \
  --lifecycle-transition autoscaling:EC2_INSTANCE_LAUNCHING \
  --heartbeat-timeout 300 \
  --default-result CONTINUE
```

Make sure your Lambda function has the necessary permissions to call
complete-lifecycle-action. After adding the hook, new instances will
wait in Pending:Wait during bootstrap.
