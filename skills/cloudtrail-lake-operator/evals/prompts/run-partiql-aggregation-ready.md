# Eval prompt: run-partiql-aggregation-ready

Plan the following PartiQL aggregation query against an existing EDS
and emit the standard VERDICT block.

Operation: run-query
EDS: arn:aws:cloudtrail:us-east-1:111111111111:event-data-store/eds-001
Region: us-east-1

```json
{
  "EDS": {
    "Status": "ENABLED",
    "EventCategory": ["Management"],
    "RetentionPeriod": 365,
    "ApproxBytesStored": 120000000000,
    "ApproxRetentionDays": 90
  },
  "SQL": "SELECT userIdentity.arn, COUNT(*) AS event_count FROM eds-001 WHERE eventTime >= date_add('day', -7, now()) GROUP BY userIdentity.arn ORDER BY event_count DESC LIMIT 20",
  "OperatorIntent": "Top 20 callers by event count in last 7 days"
}
```
