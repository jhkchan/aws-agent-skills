# Baseline (no-skill) response: composite-correlation-tiered-escalation-automated

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-notification-automator skill loaded.

---

To reduce alarm fatigue, you can build a composite alarm that ORs
several child alarms together. Then wire the composite to an SNS topic
for paging.

```bash
aws cloudwatch put-composite-alarm \
  --alarm-name prod-payment-critical-rollup \
  --alarm-rule "ALARM(rds-connections-high) OR ALARM(api-latency-p99) OR ALARM(api-5xx-rate)" \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-primary
```

For tiered escalation, you could use a Step Functions state machine
that pages the primary on-call, waits a few minutes, and then pages the
secondary if no acknowledgment is received. The state machine would
use a Wait state followed by a Choice state to check whether the
incident was acknowledged.
