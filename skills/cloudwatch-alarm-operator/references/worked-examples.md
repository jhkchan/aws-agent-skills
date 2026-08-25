# CloudWatch Alarm Operator — Worked Examples

Worked examples moved verbatim from SKILL.md (progressive disclosure). Load on demand.

## Worked example — diagnose stuck alarm (BLOCKED)

```text
OPERATION: diagnose
VERDICT: BLOCKED
TARGET: api-error-rate-prod
PRE_CHECKS:
  - [PASS] describe-alarms returns the alarm
  - [FAIL] Metric not publishing: get-metric-statistics on AWS/ApplicationELB,
    HTTPCode_ELB_5XX_Count, dimensions LoadBalancer=app/prod-alb/WRONG-NAME
    returns 0 datapoints over the last 1 hour. The LoadBalancer dimension
    value appears to reference a deleted ALB.
  - [PASS] describe-alarm-history shows INSUFFICIENT_DATA for 6 days
STEPS: (none — pre-checks failed; this is a diagnosis)
POST_VERIFY: (none)
STATE: INSUFFICIENT_DATA (stuck 6 days)
NOTES:
  - Update the dimension value to the current ALB ARN. Snapshot before update:
    aws cloudwatch describe-alarms --alarm-names api-error-rate-prod --output json > /tmp/api-error-rate-prod-backup-$(date +%s).json
```

