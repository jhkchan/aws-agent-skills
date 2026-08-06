# Eval prompt: fifo-no-dedup-config-gap

Audit the following SNS topic configuration for security exposure. Emit the
standard VERDICT block (TOPIC, VERDICT, REASON, FINDINGS, REMEDIATION).

Topic ARN: arn:aws:sns:us-east-1:111111111111:fifo-no-dedup-config-gap.fifo
Topic attributes:
  FifoTopic: true
  ContentBasedDeduplication: false
  KmsMasterKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-fifo456
  SubscriptionsConfirmed: 1
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
      "Resource": "arn:aws:sns:us-east-1:111111111111:fifo-no-dedup-config-gap.fifo"
    }
  ]
}
```
