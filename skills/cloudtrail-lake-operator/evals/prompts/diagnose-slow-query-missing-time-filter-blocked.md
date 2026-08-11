# Eval prompt: diagnose-slow-query-missing-time-filter-blocked

Diagnose why the Lake aggregation query took 11 minutes and scanned
the entire EDS. Emit the standard VERDICT block.

Operation: diagnose-slow-query
EDS: arn:aws:cloudtrail:us-east-1:111111111111:event-data-store/eds-001
Region: us-east-1

```json
{
  "EDS": {
    "Status": "ENABLED",
    "EventCategory": ["Management"],
    "ApproxBytesStored": 100000000000,
    "ApproxRetentionDays": 90
  },
  "Query": {
    "SQL": "SELECT userIdentity.arn, COUNT(*) AS cnt FROM eds-001 GROUP BY userIdentity.arn ORDER BY cnt DESC LIMIT 20"
  },
  "QueryResult": {
    "QueryStatus": "FINISHED",
    "QueryRunTimeInSeconds": 660,
    "BytesScanned": 100000000000,
    "ResultsCount": 4231
  },
  "OperatorIntent": "Top 20 callers by event count, expected under 60 second latency"
}
```
