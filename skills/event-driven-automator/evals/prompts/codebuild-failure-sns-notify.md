# Eval prompt: codebuild-failure-sns-notify

Design an EventBridge event-driven workflow for the following
scenario. Emit the standard ARCHITECTURE block (BUS, PATTERN,
TARGETS, RETRY, SAFETY, AUDIT, VERDICT, TEMPLATE).

Design reference: codebuild-failure-sns-notify
Account: 111111111111
Region: us-east-1

Source: AWS CodeBuild build state change (FAILED only)
Desired action: SNS topic that fans out to a Lambda that posts
to Slack.
The Lambda is idempotent on detail.build-id + detail.build-status.
SNS topic ARN: arn:aws:sns:us-east-1:111111111111:codebuild-events
DLQ ARN: arn:aws:sqs:us-east-1:111111111111:eventbridge-codebuild-dlq
Both pre-created.
