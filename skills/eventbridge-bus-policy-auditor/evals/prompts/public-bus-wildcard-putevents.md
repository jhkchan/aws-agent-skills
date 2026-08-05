# Eval prompt: public-bus-wildcard-putevents

Audit the following EventBridge event bus configuration for security
exposure. Emit the standard VERDICT block (BUS, VERDICT, REASON,
FINDINGS, REMEDIATION).

Event bus name: custom-bus-public-bus-wildcard-putevents
Bus ARN: arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-public-bus-wildcard-putevents
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
      "Sid": "OpenIngest",
      "Effect": "Allow",
      "Principal": {"AWS": "*"},
      "Action": "events:PutEvents",
      "Resource": "arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-public-bus-wildcard-putevents"
    }
  ]
}
```

Rules:
- Name: alert-rule
  EventPattern: {"source": ["app.alerts"]}
  Targets:
    - Id: lambda-target
      Arn: arn:aws:lambda:us-east-1:111111111111:function:alert-handler
      DeadLetterConfig: (absent)

Archive: (none configured)
