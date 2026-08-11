# Eval prompt: unconfirmed-subscription-manual-required

Validate the existing alarm-to-Slack workflow against the safety
baseline and emit the standard VERDICT block (NOTIFICATION_SOURCE,
SCOPE, VERDICT, WORKFLOW, SAFETY, FINDINGS, REMEDIATION).

Validation mode: an existing EventBridge + SNS + Lambda workflow is
reported as broken (alarms fire but Slack never receives messages).
Diagnose against the safety baseline. Region: us-east-1.
Account: 111111111111.

```json
{
  "ExistingWorkflow": {
    "EventBridgeRule": "alarm-state-change-to-sns (state ENABLED, pattern matches source=aws.cloudwatch detail.stateName=[ALARM])",
    "SNSTopic": "arn:aws:sns:us-east-1:111111111111:critical-notifications-api",
    "LambdaForwarder": "arn:aws:lambda:us-east-1:111111111111:function:alarm-slack-forwarder"
  },
  "PreFlightChecks": {
    "sns.list-subscriptions-by-topic": "Endpoint: alarm-slack-forwarder, SubscriptionArn: PendingConfirmation",
    "lambda.get-policy.alarm-slack-forwarder": "ResourceNotFoundException (no policy exists — lambda:add-permission was never run for this topic)",
    "ssm./notifications/kill-switch": "enabled",
    "ssm./slack/critical-webhook": "exists (SecureString)",
    "test-publish.NumberOfNotificationsDelivered": 0,
    "test-publish.NumberOfNotificationsFailed": 1,
    "test-publish.CloudWatchLogs": "no Lambda invocations within the last 60s"
  }
}
```
