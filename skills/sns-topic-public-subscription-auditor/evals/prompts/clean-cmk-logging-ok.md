# Eval prompt: clean-cmk-logging-ok

Audit the following SNS topic configuration for security exposure. Emit the
standard VERDICT block (TOPIC, VERDICT, REASON, FINDINGS, REMEDIATION).

Topic ARN: arn:aws:sns:us-east-1:111111111111:clean-cmk-logging-ok
Topic attributes:
  FifoTopic: false
  KmsMasterKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-clean012
  SubscriptionsConfirmed: 3
  SQSSuccessFeedbackRoleArn: arn:aws:iam::111111111111:role/SNSDeliveryFeedback
  SQSFailureFeedbackRoleArn: arn:aws:iam::111111111111:role/SNSDeliveryFeedback
  HTTPSuccessFeedbackRoleArn: arn:aws:iam::111111111111:role/SNSDeliveryFeedback
  HTTPFailureFeedbackRoleArn: arn:aws:iam::111111111111:role/SNSDeliveryFeedback

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
      "Resource": "arn:aws:sns:us-east-1:111111111111:clean-cmk-logging-ok"
    },
    {
      "Sid": "AppPublish",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-publisher"},
      "Action": [
        "sns:Publish",
        "sns:GetTopicAttributes",
        "sns:ListSubscriptionsByTopic"
      ],
      "Resource": "arn:aws:sns:us-east-1:111111111111:clean-cmk-logging-ok"
    }
  ]
}
```
