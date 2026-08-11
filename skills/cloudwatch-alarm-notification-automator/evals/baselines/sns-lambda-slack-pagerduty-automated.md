# Baseline (no-skill) response: sns-lambda-slack-pagerduty-automated

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-notification-automator skill loaded.

---

To send alarm notifications to both Slack and PagerDuty, you can
subscribe two Lambda functions to one SNS topic. One Lambda posts to
the Slack incoming webhook, the other calls the PagerDuty Events API.

```bash
aws sns create-topic --name alarm-notifications
aws sns subscribe --topic-arn <topic-arn> \
  --protocol lambda \
  --notification-endpoint <slack-lambda-arn>
aws sns subscribe --topic-arn <topic-arn> \
  --protocol lambda \
  --notification-endpoint <pagerduty-lambda-arn>
```

Then point your alarm's `--alarm-actions` at the SNS topic ARN. The
Slack Lambda should format the message with the alarm name and reason;
the PagerDuty Lambda should call
`https://events.pagerduty.com/v2/enqueue` with the routing key.

Make sure your Lambda functions have the right IAM permissions to call
Slack and PagerDuty APIs.
