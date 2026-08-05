# Eval prompt: no-encryption-aws-managed

Audit the following EventBridge event bus configuration for security
exposure. Emit the standard VERDICT block (BUS, VERDICT, REASON,
FINDINGS, REMEDIATION).

Event bus name: custom-bus-no-encryption-aws-managed
Bus ARN: arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-no-encryption-aws-managed
KmsKeyIdentifier: (absent — bus uses AWS-owned key)

Bus policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RootAccess",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "events:*",
      "Resource": "*"
    },
    {
      "Sid": "AppPublish",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-publisher"},
      "Action": "events:PutEvents",
      "Resource": "arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-no-encryption-aws-managed"
    }
  ]
}
```

Rules:
- Name: signal-rule
  EventPattern: {"source": ["app.signals"]}
  Targets:
    - Id: lambda-target
      Arn: arn:aws:lambda:us-east-1:111111111111:function:signal-handler
      DeadLetterConfig:
        Arn: arn:aws:sqs:us-east-1:111111111111:signal-dlq

Archive:
- Name: signals-archive
  EventSourceName: custom-bus-no-encryption-aws-managed
  RetentionDays: 14
