# Eval prompt: no-dlq-silent-drop

Audit the following EventBridge event bus configuration for security
exposure. Emit the standard VERDICT block (BUS, VERDICT, REASON,
FINDINGS, REMEDIATION).

Event bus name: custom-bus-no-dlq-silent-drop
Bus ARN: arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-no-dlq-silent-drop
KmsKeyIdentifier: arn:aws:kms:us-east-1:111111111111:key/cmk-eventbridge-prod

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
      "Resource": "arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-no-dlq-silent-drop"
    }
  ]
}
```

Rules:
- Name: order-processing-rule
  EventPattern: {"source": ["app.orders"]}
  Targets:
    - Id: lambda-target
      Arn: arn:aws:lambda:us-east-1:111111111111:function:order-handler
      DeadLetterConfig: (absent)
    - Id: sqs-target
      Arn: arn:aws:sqs:us-east-1:111111111111:order-queue
      DeadLetterConfig: (absent)

Archive:
- Name: orders-archive
  EventSourceName: custom-bus-no-dlq-silent-drop
  RetentionDays: 30
