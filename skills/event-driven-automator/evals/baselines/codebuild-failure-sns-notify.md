# Baseline (no-skill) response: codebuild-failure-sns-notify

This file captures what a generic assistant produces WITHOUT the
event-driven-automator skill loaded.

---

For CodeBuild failure notifications, set up an EventBridge rule on
the default bus. The source is `aws.codebuild` and the detail-type is
`CodeBuild Build State Change`. Filter on `detail.build-status: FAILED`.

Add SNS as a target — the topic fans out to Lambda which posts to
Slack.

```
aws events put-rule --name codebuild-failed --event-pattern '...'
aws events put-targets --rule codebuild-failed --targets '[...]'
```

You probably want a DLQ on the target.
