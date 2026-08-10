# Baseline (no-skill) response: dlq-missing-prerequisites

This file captures what a generic assistant produces WITHOUT the
eventbridge-rule-deployer skill loaded — note the absence of the
DLQ gap detection, the retry-policy tuning, and the idempotency
warning that the skill adds.

---

To send a Slack notification when a CodeBuild build fails, create
an EventBridge rule matching `aws.codebuild` source with
`CodeBuild Build State Change` detail-type, filtered on
`detail.build-status=FAILED`. Then add your notify-slack Lambda as
the target.

```
aws events put-rule --name codebuild-failed --event-pattern '{"source":["aws.codebuild"],...}'
aws events put-targets --rule codebuild-failed --targets '[{"Arn":"<lambda-arn>","Id":"notify"}]'
```

Make sure the Lambda has permission to be invoked by EventBridge.
