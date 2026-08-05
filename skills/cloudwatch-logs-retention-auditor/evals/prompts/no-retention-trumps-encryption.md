# Eval prompt: no-retention-trumps-encryption

Audit the following CloudWatch Logs log group configuration for cost,
security, and observability posture. Emit the standard VERDICT block
(LOG_GROUP, VERDICT, REASON, FINDINGS, REMEDIATION).

Log group name: /aws/ecs/no-retention-trumps-encryption
Log group ARN: arn:aws:logs:us-east-1:111111111111:log-group:/aws/ecs/no-retention-trumps-encryption:*

describe-log-groups output (excerpt):

```json
{
  "logGroupName": "/aws/ecs/no-retention-trumps-encryption",
  "creationTime": 1690000000000,
  "storedBytes": 52428800
}
```

Note: both the `retentionInDays` field and the `kmsKeyId` field are
absent from the describe-log-groups output above.

Metric filters: 0
Subscription filters: 0
Anomaly detectors: 0
