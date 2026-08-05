# Eval prompt: ok-org-scoped-bus

Audit the following EventBridge event bus configuration for security
exposure. Emit the standard VERDICT block (BUS, VERDICT, REASON,
FINDINGS, REMEDIATION).

Event bus name: custom-bus-ok-org-scoped-bus
Bus ARN: arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-ok-org-scoped-bus
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
      "Sid": "CrossAccountOrgScoped",
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:role/app-publisher"},
      "Action": "events:PutEvents",
      "Resource": "arn:aws:events:us-east-1:111111111111:event-bus/custom-bus-ok-org-scoped-bus",
      "Condition": {
        "StringEquals": {
          "aws:PrincipalOrgID": "o-aabbccdded"
        }
      }
    }
  ]
}
```

Rules:
- Name: ingest-rule
  EventPattern: {"source": ["app.ingest"]}
  Targets:
    - Id: lambda-target
      Arn: arn:aws:lambda:us-east-1:111111111111:function:ingest-handler
      DeadLetterConfig:
        Arn: arn:aws:sqs:us-east-1:111111111111:ingest-dlq

Archive:
- Name: ingest-archive
  EventSourceName: custom-bus-ok-org-scoped-bus
  RetentionDays: 30
