# Baseline (no-skill) response: diagnose-slow-query-missing-time-filter-blocked

This file captures what a generic assistant produces WITHOUT the
cloudtrail-lake-operator skill loaded.

---

Your query is slow because it scans the entire EDS. Try adding a
time filter:

```sql
SELECT userIdentity.arn, COUNT(*) AS cnt
FROM eds-001
WHERE eventTime >= date_add('day', -30, now())
GROUP BY userIdentity.arn
ORDER BY cnt DESC
LIMIT 20
```

Also consider narrowing the columns you select. Lake is columnar so
fewer columns means less data scanned.
