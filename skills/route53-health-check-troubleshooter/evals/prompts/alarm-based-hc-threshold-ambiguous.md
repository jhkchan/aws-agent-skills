# Eval prompt: alarm-based-hc-threshold-ambiguous

Diagnose the Route 53 health check failure for the following scenario.
Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: Route 53 CloudWatch alarm-based health check is not
triggering DNS failover even though the primary endpoint appears
unhealthy. The health check stays healthy.

```text
HealthCheckId: hc-alarm-ambiguous
Type: CLOUDWATCH_METRIC
AlarmIdentifier:
  Name: not provided
  Region: us-east-1

Missing context:
  - Alarm name: not provided
  - Alarm metric name and namespace: not provided
  - Alarm period: not provided
  - Alarm evaluation periods: not provided
  - Alarm datapoints to alarm: not provided
  - Alarm threshold and comparison operator: not provided
  - Current alarm state (OK / ALARM / INSUFFICIENT_DATA): not provided
  - Alarm history (describe-alarm-history): not provided
```

The operator says the endpoint is "unhealthy" but has not verified what
metric the alarm monitors, whether the alarm threshold is correct, or
whether the alarm is in ALARM state. Without the alarm configuration
and current state, it is impossible to determine whether the alarm
threshold is wrong, the alarm metric is irrelevant, or the alarm is
in INSUFFICIENT_DATA state (which does not trigger failover). Emit
INSUFFICIENT_DATA with the specific missing fields needed to proceed.
