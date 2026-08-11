# Eval prompt: diagnose-empty-query-event-category-mismatch-blocked

Diagnose why the Lake query for S3 object-level events returned zero
rows. Emit the standard VERDICT block.

Operation: diagnose-empty-query
EDS: arn:aws:cloudtrail:us-east-1:111111111111:event-data-store/eds-001
  (name: org-governance-edS)
Region: us-east-1

```json
{
  "EDS": {
    "Status": "ENABLED",
    "EventCategory": ["Management"],
    "RetentionPeriod": 365,
    "TerminationProtectionEnabled": true
  },
  "Query": {
    "SQL": "SELECT userIdentity.accountId, eventName, COUNT(*) FROM eds-001 WHERE eventTime >= '2026-08-01' AND eventSource = 's3.amazonaws.com' GROUP BY userIdentity.accountId, eventName"
  },
  "QueryResult": {
    "QueryStatus": "FINISHED",
    "QueryRunTimeInSeconds": 14,
    "BytesScanned": 4200000000,
    "ResultsCount": 0
  },
  "OperatorIntent": "Count S3 GetObject/PutObject/DeleteObject events per account"
}
```
