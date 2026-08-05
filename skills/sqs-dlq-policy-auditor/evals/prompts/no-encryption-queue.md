# Eval prompt: no-encryption-queue

Audit the following SQS queue configuration for security exposure and DLQ
health. Emit the standard VERDICT block (QUEUE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Queue URL: https://sqs.us-east-1.amazonaws.com/111111111111/no-encryption-queue
QueueArn: arn:aws:sqs:us-east-1:111111111111:no-encryption-queue
Attributes:
  Policy: (empty — no resource-based queue policy)
  RedrivePolicy:
    ```json
    {"deadLetterTargetArn": "arn:aws:sqs:us-east-1:111111111111:no-encryption-queue-dlq", "maxReceiveCount": "5"}
    ```
  KmsMasterKeyId: (not set)
  SqsManagedSseEnabled: false
  MessageRetentionPeriod: "345600"
  VisibilityTimeout: "30"
