# Eval prompt: sns-lambda-slack-pagerduty-automated

Plan the following CloudWatch alarm notification workflow design and
emit the standard VERDICT block (NOTIFICATION_SOURCE, SCOPE, VERDICT,
WORKFLOW, SAFETY, FINDINGS, REMEDIATION).

Design intent: wire the prod-checkout-critical-rollup composite alarm
to Slack #ops-alerts AND PagerDuty service PXYZ. 1-tier (no escalation).
Region: us-east-1. Account: 111111111111.

```json
{
  "SourceComposite": {
    "alarmName": "prod-checkout-critical-rollup",
    "stateValue": "OK",
    "alarmRule": "ALARM(alb-error-ratio-prod) OR ALARM(alb-latency-anomaly-prod) OR ALARM(lambda-errors-high-prod-checkout)"
  },
  "PreFlightChecks": {
    "sns.list-topics": "arn:aws:sns:us-east-1:111111111111:critical-notifications-checkout exists",
    "lambda.list-functions": ["alarm-slack-forwarder (python3.11, 10s timeout)", "alarm-pagerduty-forwarder (python3.11, 10s timeout)"],
    "sns.list-subscriptions-by-topic": [
      "alarm-slack-forwarder: SubscriptionArn populated (confirmed)",
      "alarm-pagerduty-forwarder: SubscriptionArn populated (confirmed)"
    ],
    "lambda.get-policy.alarm-slack-forwarder": "AllowSNSInvoke present with source-arn matching",
    "lambda.get-policy.alarm-pagerduty-forwarder": "AllowSNSInvoke present with source-arn matching",
    "ssm./notifications/kill-switch": "enabled",
    "ssm./slack/critical-webhook": "exists (SecureString)",
    "ssm./pagerduty/integration-key": "exists (SecureString)",
    "test-publish": "delivered to Slack in 8s, PagerDuty incident created in 11s"
  }
}
```
