# Baseline (no-skill) response: severity-routing-lambda

This file captures what a generic assistant produces WITHOUT the
cost-anomaly-detection-automator skill loaded.

---

For severity routing, you can create three anomaly subscriptions with
different thresholds. Critical goes to PagerDuty, High goes to Slack,
and Low just gets logged.

You'll need a Lambda function that reads the SNS message and decides
where to send it based on the impact amount. Use the Slack webhook to
send notifications to the right channel.

The subscriptions would look something like:

```
aws ce create-anomaly-subscription --anomaly-subscription ...
```

I'm not sure about the exact threshold format or how to map the impact
to severity levels. You'll need to figure out the right percentages.
