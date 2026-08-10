# Eval prompt: guardduty-lambda-ready-to-deploy

Design an EventBridge rule deployment for the following scenario.
Emit the standard PLAN block (RULE, TARGETS, RETRY, DLQ,
INPUT_TRANSFORM, PREREQUISITES, VERDICT, GAP, TEMPLATE).

Design reference: guardduty-lambda-ready-to-deploy
Account: 111111111111
Region: us-east-1

Source: AWS GuardDuty high-severity findings (severity >= 7)
Desired action: invoke Lambda `isolate-instance` to move the
implicated EC2 instance into an isolation security group.
The Lambda is idempotent (dedupes on finding-id) and tested.
DLQ: arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-dlq
  (already created with 14-day retention).
Lambda ARN: arn:aws:lambda:us-east-1:111111111111:function:isolate-instance
Lambda invocation permission for events.amazonaws.com: already granted.
