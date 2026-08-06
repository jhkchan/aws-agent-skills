# Eval prompt: wildcard-sns-all-no-encryption

Audit the following SNS topic configuration for security exposure. Emit the
standard VERDICT block (TOPIC, VERDICT, REASON, FINDINGS, REMEDIATION).

Topic ARN: arn:aws:sns:us-east-1:111111111111:wildcard-sns-all-no-encryption
Topic attributes:
  FifoTopic: false
  KmsMasterKeyId: (empty — no encryption configured)
  SubscriptionsConfirmed: 5

Topic policy (default):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OpenAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sns:*",
      "Resource": "arn:aws:sns:us-east-1:111111111111:wildcard-sns-all-no-encryption"
    }
  ]
}
```
