# Eval prompt: public-bus-weak-source-ip

Audit the following EventBridge event bus configuration for security
exposure. Emit the standard VERDICT block (BUS, VERDICT, REASON,
FINDINGS, REMEDIATION).

Event bus name: custom-bus-public-bus-weak-source-ip
Bus ARN: arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-public-bus-weak-source-ip
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
      "Sid": "IpRestrictedIngest",
      "Effect": "Allow",
      "Principal": {"AWS": "*"},
      "Action": "events:PutEvents",
      "Resource": "arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-public-bus-weak-source-ip",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": "0.0.0.0/0"
        }
      }
    }
  ]
}
```

Rules:
- Name: webhook-rule
  EventPattern: {"source": ["app.webhooks"]}
  Targets:
    - Id: lambda-target
      Arn: arn:aws:lambda:us-east-1:111111111111:function:webhook-handler
      DeadLetterConfig:
        Arn: arn:aws:sqs:us-east-1:111111111111:webhook-dlq

Archive:
- Name: webhooks-archive
  EventSourceName: custom-bus-public-bus-weak-source-ip
  RetentionDays: 7
