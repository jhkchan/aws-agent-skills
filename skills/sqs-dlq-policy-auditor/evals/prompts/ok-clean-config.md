# Eval prompt: ok-clean-config

Audit the following SQS queue configuration for security exposure and DLQ
health. Emit the standard VERDICT block (QUEUE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Queue URL: https://sqs.us-east-1.amazonaws.com/111111111111/ok-clean-config
QueueArn: arn:aws:sqs:us-east-1:111111111111:ok-clean-config
Attributes:
  Policy:
    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "AppConsumer",
          "Effect": "Allow",
          "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-consumer"},
          "Action": ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
          "Resource": "arn:aws:sqs:us-east-1:111111111111:ok-clean-config"
        }
      ]
    }
    ```
  RedrivePolicy:
    ```json
    {"deadLetterTargetArn": "arn:aws:sqs:us-east-1:111111111111:ok-clean-config-dlq", "maxReceiveCount": "5"}
    ```
  SqsManagedSseEnabled: true
  MessageRetentionPeriod: "345600"
  VisibilityTimeout: "30"

DLQ attributes:
  QueueArn: arn:aws:sqs:us-east-1:111111111111:ok-clean-config-dlq
  MessageRetentionPeriod: "1209600"
