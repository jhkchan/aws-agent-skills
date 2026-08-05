# Eval prompt: long-retention-cost-risk

Audit the following CloudWatch Logs log group configuration for cost,
security, and observability posture. Emit the standard VERDICT block
(LOG_GROUP, VERDICT, REASON, FINDINGS, REMEDIATION).

Log group name: /prod/long-retention-cost-risk
Log group ARN: arn:aws:logs:us-east-1:111111111111:log-group:/prod/long-retention-cost-risk:*

describe-log-groups output (excerpt):

```json
{
  "logGroupName": "/prod/long-retention-cost-risk",
  "creationTime": 1600000000000,
  "retentionInDays": 3650,
  "kmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/cmk-456",
  "storedBytes": 268435456000
}
```

Metric filters: 1 (filterName: WarnCount, filterPattern: "WARN")
Subscription filters: 0
Anomaly detectors: 0
