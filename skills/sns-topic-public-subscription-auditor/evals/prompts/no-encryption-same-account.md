# Eval prompt: no-encryption-same-account

Audit the following SNS topic configuration for security exposure. Emit the
standard VERDICT block (TOPIC, VERDICT, REASON, FINDINGS, REMEDIATION).

Topic ARN: arn:aws:sns:us-east-1:111111111111:no-encryption-same-account
Topic attributes:
  FifoTopic: false
  KmsMasterKeyId: (empty — no encryption configured)
  SubscriptionsConfirmed: 2
  SQSSuccessFeedbackRoleArn: arn:aws:iam::111111111111:role/SNSDeliveryFeedback
  SQSFailureFeedbackRoleArn: arn:aws:iam::111111111111:role/SNSDeliveryFeedback

Topic policy (default):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RootAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "sns:*",
      "Resource": "arn:aws:sns:us-east-1:111111111111:no-encryption-same-account"
    },
    {
      "Sid": "AppPublish",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-publisher"},
      "Action": [
        "sns:Publish",
        "sns:GetTopicAttributes"
      ],
      "Resource": "arn:aws:sns:us-east-1:111111111111:no-encryption-same-account"
    }
  ]
}
```
