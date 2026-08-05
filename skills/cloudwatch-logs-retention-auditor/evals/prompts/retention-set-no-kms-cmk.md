# Eval prompt: retention-set-no-kms-cmk

Audit the following CloudWatch Logs log group configuration for cost,
security, and observability posture. Emit the standard VERDICT block
(LOG_GROUP, VERDICT, REASON, FINDINGS, REMEDIATION).

Log group name: /app/retention-set-no-kms-cmk
Log group ARN: arn:aws:logs:us-east-1:111111111111:log-group:/app/retention-set-no-kms-cmk:*

describe-log-groups output (excerpt):

```json
{
  "logGroupName": "/app/retention-set-no-kms-cmk",
  "creationTime": 1710000000000,
  "retentionInDays": 90,
  "storedBytes": 1073741824
}
```

Note: the `kmsKeyId` field is absent from the describe-log-groups output
above.

Metric filters: 1 (filterName: ApiErrors, filterPattern: "ERROR")
Subscription filters: 0
Anomaly detectors: 0
