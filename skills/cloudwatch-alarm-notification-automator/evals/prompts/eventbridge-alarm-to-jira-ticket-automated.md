# Eval prompt: eventbridge-alarm-to-jira-ticket-automated

Plan the following alarm-to-Jira ticket automation and emit the
standard VERDICT block (NOTIFICATION_SOURCE, SCOPE, VERDICT, WORKFLOW,
SAFETY, FINDINGS, REMEDIATION).

Design intent: auto-create a Jira Incident ticket in project OPS when
the prod-checkout-critical-rollup composite enters ALARM, auto-resolve
when it returns to OK. Region: us-east-1. Account: 111111111111.

```json
{
  "SourceComposite": {
    "alarmName": "prod-checkout-critical-rollup"
  },
  "PreFlightChecks": {
    "events.describe-rule.alarm-state-change-to-jira": "state ENABLED, pattern matches source=aws.cloudwatch detail-type=CloudWatch Alarm State Change detail.stateName=[ALARM,OK]",
    "events.list-targets-by-rule": "Target: arn:aws:lambda:us-east-1:111111111111:function:alarm-jira-creator",
    "lambda.get-policy.alarm-jira-creator": "AllowEventBridgeInvoke statement present",
    "ssm./jira/api-token": "exists (SecureString)",
    "ssm./jira/email": "exists (String)",
    "dynamodb.describe-table.alarm-ticket-map": "ACTIVE, KeySchema: alarmName (HASH)",
    "test-alarm-event": "Jira ticket OPS-123 created, recorded in DynamoDB",
    "test-duplicate-event": "DynamoDB dedup hit, no duplicate ticket created",
    "test-ok-transition": "Jira ticket OPS-123 transitioned to Resolved (state=31)"
  }
}
```
