# Baseline (no-skill) response: eventbridge-alarm-to-jira-ticket-automated

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-notification-automator skill loaded.

---

To auto-create a Jira ticket when a CloudWatch alarm fires, create an
EventBridge rule that matches the alarm state change event and targets
a Lambda function. The Lambda calls the Jira REST API to create an
issue.

```bash
aws events put-rule --name alarm-to-jira \
  --event-pattern '{"source": ["aws.cloudwatch"], "detail-type": ["CloudWatch Alarm State Change"], "detail": {"stateName": ["ALARM"]}}'

aws events put-targets --rule alarm-to-jira \
  --targets '[{"Id": "jira-lambda", "Arn": "<lambda-arn>"}]'
```

The Lambda should POST to
`https://your-domain.atlassian.net/rest/api/3/issue` with the project
key, summary, and description from the alarm event. Store the Jira API
token in an environment variable.
