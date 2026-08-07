# Baseline (no-skill) response: composite-alarm-reduce-fatigue-ready

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-operator skill loaded.

---

To create a composite alarm that rolls up your three child alarms,
use:

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name prod-checkout-critical-rollup \
  --alarm-rule "ALARM(alb-error-ratio-prod) OR ALARM(alb-latency-anomaly-prod) OR ALARM(lambda-errors-high-prod-checkout)" \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-escalation
```

This will fire the escalation SNS topic whenever any of the three
child alarms goes into ALARM state.
