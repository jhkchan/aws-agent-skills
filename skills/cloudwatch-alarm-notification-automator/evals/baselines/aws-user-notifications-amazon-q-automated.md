# Baseline (no-skill) response: aws-user-notifications-amazon-q-automated

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-notification-automator skill loaded.

---

AWS User Notifications can deliver CloudWatch alarm state changes to
Slack via Chatbot without writing a Lambda function. You can configure
this from the AWS Console under User Notifications, or via the CLI.

Amazon Q can help triage alarms by analyzing related logs and metrics.
You can enable Q operational analysis on your application in the
CloudWatch console.

To set this up:

1. Create a notification hub in your region.
2. Configure a Chatbot Slack channel configuration pointing to your
   Slack workspace and channel.
3. Set the alarm's action to publish to the Chatbot SNS topic.
4. Enable Amazon Q operational analysis on the application.

This avoids the need to maintain a custom Lambda forwarder for standard
alarm-to-Slack delivery.
