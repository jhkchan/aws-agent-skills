# Eval prompt: composite-correlation-tiered-escalation-automated

Plan the following composite alarm correlation + 2-tier escalation
design and emit the standard VERDICT block (NOTIFICATION_SOURCE, SCOPE,
VERDICT, WORKFLOW, SAFETY, FINDINGS, REMEDIATION).

Design intent: build a composite alarm (prod-payment-critical-rollup)
that OR-correlates three child alarms (rds-connections-high,
api-latency-p99, api-5xx-rate). Wire the composite to a 2-tier
escalation (primary -> 5 min wait -> secondary if unacked) via Step
Functions. Region: us-east-1. Account: 111111111111.

```json
{
  "ChildAlarms": [
    {"name": "rds-connections-high", "state": "OK"},
    {"name": "api-latency-p99", "state": "OK"},
    {"name": "api-5xx-rate", "state": "OK"}
  ],
  "Composite": {"name": "prod-payment-critical-rollup", "exists": false},
  "PreFlightChecks": {
    "stepfunctions.describe-state-machine.payment-escalation": "ACTIVE, definition includes PagePrimary -> WaitForAck 300s -> CheckAck Choice -> PageSecondary",
    "sns.list-topics": [
      "arn:aws:sns:us-east-1:111111111111:on-call-primary (3 subscriptions)",
      "arn:aws:sns:us-east-1:111111111111:on-call-secondary (2 subscriptions)"
    ],
    "dynamodb.describe-table.alarm-ack-state": "ACTIVE (key: incidentId)",
    "ssm./notifications/kill-switch": "enabled",
    "test-escalation": "primary paged in 4s, ack recorded via API Gateway within 60s, state machine exited without escalating"
  }
}
```
