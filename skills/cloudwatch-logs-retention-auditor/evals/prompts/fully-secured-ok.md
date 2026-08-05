# Eval prompt: fully-secured-ok

Audit the following CloudWatch Logs log group configuration for cost,
security, and observability posture. Emit the standard VERDICT block
(LOG_GROUP, VERDICT, REASON, FINDINGS, REMEDIATION).

Log group name: /prod/fully-secured-ok
Log group ARN: arn:aws:logs:us-east-1:111111111111:log-group:/prod/fully-secured-ok:*

describe-log-groups output (excerpt):

```json
{
  "logGroupName": "/prod/fully-secured-ok",
  "creationTime": 1700000000000,
  "retentionInDays": 90,
  "kmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/cmk-aaa",
  "storedBytes": 524288000
}
```

Metric filters: 1 (filterName: ErrorCount, filterPattern: "ERROR")
Subscription filters: 0
Anomaly detectors: 1 (detectorName: prod-anomaly, status: ACTIVE, evalFrequency: ONE_MIN)
