# Baseline (no-skill) response: action-sns-policy-missing

---

Your alarm is firing but no Slack notification is going out. Check
the SNS topic subscriptions — make sure the Slack endpoint (Lambda or
webhook) is subscribed and Confirmed. Also check that the SNS topic
ARN in AlarmActions is correct and points to the right topic.

If the subscription looks fine, try publishing a test message to the
SNS topic from the CLI to verify the topic itself is working. You
could also check CloudWatch Logs for any Lambda delivery errors.
