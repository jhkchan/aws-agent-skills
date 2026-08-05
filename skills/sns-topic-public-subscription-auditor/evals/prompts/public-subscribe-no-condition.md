# Eval prompt: public-subscribe-no-condition

Audit the following SNS topic configuration for security exposure. Emit the
standard VERDICT block (TOPIC, VERDICT, REASON, FINDINGS, REMEDIATION).

Topic ARN: arn:aws:sns:us-east-1:111111111111:public-subscribe-no-condition
Topic attributes:
  FifoTopic: false
  KmsMasterKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-abc123
  SubscriptionsConfirmed: 3
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
      "Resource": "arn:aws:sns:us-east-1:111111111111:public-subscribe-no-condition"
    },
    {
      "Sid": "OpenSubscribe",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "sns:Subscribe",
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:us-east-1:111111111111:public-subscribe-no-condition"
    }
  ]
}
```
