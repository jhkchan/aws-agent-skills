# Eval prompt: public-source-arn-still-ok

Audit the following SQS queue configuration for security exposure and DLQ
health. Emit the standard VERDICT block (QUEUE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Queue URL: https://sqs.us-east-1.amazonaws.com/111111111111/public-source-arn-still-ok
QueueArn: arn:aws:sqs:us-east-1:111111111111:public-source-arn-still-ok
Attributes:
  Policy:
    ```json
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "S3Notification",
          "Effect": "Allow",
          "Principal": "*",
          "Action": "sqs:SendMessage",
          "Resource": "arn:aws:sqs:us-east-1:111111111111:public-source-arn-still-ok",
          "Condition": {
            "ArnEquals": {"aws:SourceArn": "arn:aws:s3:::notification-source-bucket"}
          }
        }
      ]
    }
    ```
  RedrivePolicy:
    ```json
    {"deadLetterTargetArn": "arn:aws:sqs:us-east-1:111111111111:public-source-arn-still-ok-dlq", "maxReceiveCount": "5"}
    ```
  SqsManagedSseEnabled: true
  MessageRetentionPeriod: "345600"
  VisibilityTimeout: "30"

DLQ attributes:
  QueueArn: arn:aws:sqs:us-east-1:111111111111:public-source-arn-still-ok-dlq
  MessageRetentionPeriod: "1209600"
