# Eval prompt: aws-user-notifications-amazon-q-automated

Plan the following AWS User Notifications + Amazon Q design and emit
the standard VERDICT block (NOTIFICATION_SOURCE, SCOPE, VERDICT,
WORKFLOW, SAFETY, FINDINGS, REMEDIATION).

Design intent: deliver CloudWatch alarm notifications for the
prod-checkout service to Slack #ops-alerts via AWS User Notifications
(Chatbot), and add Amazon Q operational analysis for triage. No custom
Lambda forwarder. Region: us-east-1. Account: 111111111111.

```json
{
  "Service": "prod-checkout",
  "PreFlightChecks": {
    "notifications.list-notification-hubs": "arn:aws:notifications::111111111111:hub/prod (status ACTIVE)",
    "chatbot.describe-slack-channel-configurations": {
      "ConfigurationName": "prod-alarm-slack",
      "SlackWorkspaceId": "T0XXXXXXXX",
      "SlackChannelId": "C0XXXXXXXX (#ops-alerts)",
      "SnsTopicArns": ["arn:aws:sns:us-east-1:111111111111:aws-chatbot"],
      "IamRoleArn": "arn:aws:iam::111111111111:role/aws-chatbot-role"
    },
    "cloudwatch.describe-alarms.prod-checkout-critical-rollup": "OK, AlarmActions includes arn:aws:sns:us-east-1:111111111111:aws-chatbot",
    "application-signals.get-application.prod-checkout": "OperationalAnalysisConfig.enabled = true",
    "test-publish": "Slack message arrived in #ops-alerts in 6s (Chatbot-formatted), Amazon Q analysis link populated with deployment correlation + log errors within 45s",
    "sns.list-subscriptions-by-topic.aws-chatbot": "1 subscription (Chatbot-managed, confirmed)",
    "ssm./notifications/kill-switch": "enabled"
  }
}
```
