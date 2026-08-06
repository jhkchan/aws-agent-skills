# Eval prompt: no-dlq-configured

Audit the following SQS queue configuration for security exposure and DLQ
health. Emit the standard VERDICT block (QUEUE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Queue URL: https://sqs.us-east-1.amazonaws.com/111111111111/no-dlq-configured
QueueArn: arn:aws:sqs:us-east-1:111111111111:no-dlq-configured
Attributes:
  Policy: (empty — no resource-based queue policy)
  RedrivePolicy: (not set)
  SqsManagedSseEnabled: true
  MessageRetentionPeriod: "345600"
  VisibilityTimeout: "30"
