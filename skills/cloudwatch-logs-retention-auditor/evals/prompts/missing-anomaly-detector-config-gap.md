# Eval prompt: missing-anomaly-detector-config-gap

Audit the following CloudWatch Logs log group configuration for cost,
security, and observability posture. Emit the standard VERDICT block
(LOG_GROUP, VERDICT, REASON, FINDINGS, REMEDIATION).

Log group name: /svc/missing-anomaly-detector-config-gap
Log group ARN: arn:aws:logs:us-east-1:111111111111:log-group:/svc/missing-anomaly-detector-config-gap:*

describe-log-groups output (excerpt):

```json
{
  "logGroupName": "/svc/missing-anomaly-detector-config-gap",
  "creationTime": 1715000000000,
  "retentionInDays": 90,
  "kmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/cmk-789",
  "storedBytes": 2147483648
}
```

Metric filters: 1 (filterName: ErrorCount, filterPattern: "ERROR")
Subscription filters: 0
Anomaly detectors: 0
