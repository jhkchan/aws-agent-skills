# Eval prompt: dlq-missing-prerequisites

Design an EventBridge rule deployment for the following scenario.
Emit the standard PLAN block and identify any gaps.

Design reference: dlq-missing-prerequisites
Account: 111111111111
Region: us-east-1

Source: AWS CodeBuild build state change (FAILED only)
Desired action: invoke Lambda `notify-slack` to post to a Slack
channel whenever a build fails.
The Lambda is NOT idempotent (no dedup on build-id).
DLQ: NONE (not yet created).
Lambda ARN: arn:aws:lambda:us-east-1:111111111111:function:notify-slack
Lambda invocation permission for events.amazonaws.com: granted.

Emit the standard PLAN block. Identify any gaps that block
READY_TO_DEPLOY and provide specific remediation.
