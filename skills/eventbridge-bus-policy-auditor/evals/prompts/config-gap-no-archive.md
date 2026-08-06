# Eval prompt: config-gap-no-archive

Audit the following EventBridge event bus configuration for security
exposure. Emit the standard VERDICT block (BUS, VERDICT, REASON,
FINDINGS, REMEDIATION).

Event bus name: custom-bus-config-gap-no-archive
Bus ARN: arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-config-gap-no-archive
KmsKeyIdentifier: arn:aws:kms:us-east-1:111111111111:key/cmk-eventbridge-staging

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
      "Resource": "arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-config-gap-no-archive"
    }
  ]
}
```

Rules:
- Name: notify-rule
  EventPattern: {"source": ["app.notify"]}
  Targets:
    - Id: lambda-target
      Arn: arn:aws:lambda:us-east-1:111111111111:function:notify-handler
      DeadLetterConfig:
        Arn: arn:aws:sqs:us-east-1:111111111111:notify-dlq

Archive: (none configured)
