# Eval prompt: public-access-no-condition

Audit the following SQS queue configuration for security exposure and DLQ
health. Emit the standard VERDICT block (QUEUE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Queue URL: https://sqs.us-east-1.amazonaws.com/111111111111/public-access-no-condition
QueueArn: arn:aws:sqs:us-east-1:111111111111:public-access-no-condition
Attributes:
  Policy:
    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "OpenSend",
          "Effect": "Allow",
          "Principal": "*",
          "Action": "sqs:SendMessage",
          "Resource": "arn:aws:sqs:us-east-1:111111111111:public-access-no-condition"
        }
      ]
    }
    ```
  RedrivePolicy:
    ```json
    {"deadLetterTargetArn": "arn:aws:sqs:us-east-1:111111111111:public-access-no-condition-dlq", "maxReceiveCount": "5"}
    ```
  SqsManagedSseEnabled: true
  MessageRetentionPeriod: "345600"
  VisibilityTimeout: "30"
