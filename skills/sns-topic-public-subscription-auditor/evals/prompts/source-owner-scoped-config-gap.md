# Eval prompt: source-owner-scoped-config-gap

Audit the following SNS topic configuration for security exposure. Emit the
standard VERDICT block (TOPIC, VERDICT, REASON, FINDINGS, REMEDIATION).

Topic ARN: arn:aws:sns:us-east-1:111111111111:source-owner-scoped-config-gap
Topic attributes:
  FifoTopic: false
  KmsMasterKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-scoped789
  SubscriptionsConfirmed: 4

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
      "Resource": "arn:aws:sns:us-east-1:111111111111:source-owner-scoped-config-gap"
    },
    {
      "Sid": "ScopedPublish",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:111111111111:source-owner-scoped-config-gap",
      "Condition": {
        "StringEquals": {
          "aws:SourceOwner": "111111111111"
        }
      }
    }
  ]
}
```
