# Baseline (no-skill) response: unconfirmed-subscription-manual-required

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-notification-automator skill loaded.

---

If alarms are firing but Slack is not receiving messages, check whether
the SNS subscription is confirmed. You can verify with:

```bash
aws sns list-subscriptions-by-topic --topic-arn <topic-arn>
```

If the `SubscriptionArn` shows `PendingConfirmation`, the subscription
needs to be confirmed. For Lambda subscriptions, also make sure the
Lambda has permission to be invoked by SNS. You may need to check the
CloudWatch Logs for the Lambda function to see if it is being invoked.

Also verify that the alarm's `--alarm-actions` includes the SNS topic
ARN and that `ActionsEnabled` is true on the alarm.
