# Eval prompt: config-gap-maxreceive-one

Audit the following SQS queue configuration for security exposure and DLQ
health. Emit the standard VERDICT block (QUEUE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Queue URL: https://sqs.us-east-1.amazonaws.com/111111111111/config-gap-maxreceive-one
QueueArn: arn:aws:sqs:us-east-1:111111111111:config-gap-maxreceive-one
Attributes:
  Policy: (empty — no resource-based queue policy)
  RedrivePolicy:
    ```json
    {"deadLetterTargetArn": "arn:aws:sqs:us-east-1:111111111111:config-gap-maxreceive-one-dlq", "maxReceiveCount": "1"}
    ```
  SqsManagedSseEnabled: true
  MessageRetentionPeriod: "345600"
  VisibilityTimeout: "30"

DLQ attributes:
  QueueArn: arn:aws:sqs:us-east-1:111111111111:config-gap-maxreceive-one-dlq
  MessageRetentionPeriod: "86400"
