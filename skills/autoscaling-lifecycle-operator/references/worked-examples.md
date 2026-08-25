# Auto Scaling Lifecycle Hook Operator — Worked Examples

Secondary worked examples moved from SKILL.md. The primary worked example
(add-launch-hook, OPERATION_COMPLETED) remains in SKILL.md.


## Worked example — diagnose-stuck (REVIEW_REQUIRED) (moved from SKILL.md)

```text
OPERATION: diagnose-stuck
VERDICT: REVIEW_REQUIRED
TARGET: prod-api-asg (hook: api-bootstrap-hook)
PRE_CHECKS:
  - [PASS] ASG exists, DesiredCapacity: 6
  - [PASS] Hook api-bootstrap-hook exists (HeartbeatTimeout 3600)
  - [FAIL] Instance i-xxx stuck in Pending:Wait for 42 minutes
  - [FAIL] Lambda timed out after 30s — bootstrap takes ~45s
STEPS: (none — root cause is Lambda timeout too short)
NOTES:
  - Fix: increase Lambda timeout to 60s, then manually complete:
    aws lambda update-function-configuration --function-name api-lifecycle-action --timeout 60
    aws autoscaling complete-lifecycle-action \
      --lifecycle-hook-name api-bootstrap-hook --auto-scaling-group-name prod-api-asg \
      --lifecycle-action-token <token> --lifecycle-action-result CONTINUE
  - Also reduce HeartbeatTimeout from 3600 to 300.
```
