# Baseline (no-skill) response: run-partiql-aggregation-ready

This file captures what a generic assistant produces WITHOUT the
cloudtrail-lake-operator skill loaded.

---

To run the aggregation query, use:

```bash
aws cloudtrail start-query \
  --query-statement "SELECT userIdentity.arn, COUNT(*) AS event_count FROM eds-001 WHERE eventTime >= date_add('day', -7, now()) GROUP BY userIdentity.arn ORDER BY event_count DESC LIMIT 20"
```

Then poll with `describe-query` until `QueryStatus: FINISHED` and
fetch results via `get-query-results`.
