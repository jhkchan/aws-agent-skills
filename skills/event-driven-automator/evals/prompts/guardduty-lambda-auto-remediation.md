# Eval prompt: guardduty-lambda-auto-remediation

Design an EventBridge event-driven workflow for the following
scenario. Emit the standard ARCHITECTURE block (BUS, PATTERN,
TARGETS, RETRY, SAFETY, AUDIT, VERDICT, TEMPLATE).

Design reference: guardduty-lambda-auto-remediation
Account: 111111111111
Region: us-east-1

Source: AWS GuardDuty high-severity findings (severity >= 7)
Desired action: invoke Lambda `isolate-instance` to move the
implicated EC2 instance into an isolation security group.
The Lambda is idempotent (dedupes on finding-id) and tested.
DLQ: arn:aws:sqs:us-east-1:111111111111:eventbridge-guardduty-dlq
  (already created).
Lambda ARN: arn:aws:lambda:us-east-1:111111111111:function:isolate-instance
