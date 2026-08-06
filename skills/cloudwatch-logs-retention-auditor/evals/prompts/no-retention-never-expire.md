# Eval prompt: no-retention-never-expire

Audit the following CloudWatch Logs log group configuration for cost,
security, and observability posture. Emit the standard VERDICT block
(LOG_GROUP, VERDICT, REASON, FINDINGS, REMEDIATION).

Log group name: /aws/lambda/no-retention-never-expire
Log group ARN: arn:aws:logs:us-east-1:111111111111:log-group:/aws/lambda/no-retention-never-expire:*

describe-log-groups output (excerpt):

```json
{
  "logGroupName": "/aws/lambda/no-retention-never-expire",
  "creationTime": 1700000000000,
  "kmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/cmk-123",
  "storedBytes": 524288000
}
```

Note: the `retentionInDays` field is absent from the describe-log-groups
output above.

Metric filters: 1 (filterName: ErrorCount, filterPattern: "ERROR")
Subscription filters: 0
Anomaly detectors: 0
