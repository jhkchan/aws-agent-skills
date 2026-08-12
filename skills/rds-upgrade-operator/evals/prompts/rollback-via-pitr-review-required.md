# Eval prompt: rollback-via-pitr-review-required

Plan the following RDS rollback via point-in-time recovery after a query
performance regression and emit the standard VERDICT block (OPERATION,
VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: rollback
Instance: prod-orders-db
Current engine version: 15.4 (upgraded from 14.11)
Restore target: PostgreSQL 14.11 state at 2026-08-04 02:50 UTC

```json
{
  "PreUpgradeSnapshot": {
    "prod-orders-db-pre-15-4": "available (taken 2026-08-04 02:55 UTC)"
  },
  "PITRWindowCheck": {
    "2026-08-04T02:50:00Z is within the 35-day backup retention period": true,
    "CurrentDate": "2026-08-11"
  },
  "PostUpgradeRegression": {
    "Top3Queries": "8x latency increase (Performance Insights)",
    "RootCause": "pg_upgrade rebuilt planner statistics; ANALYZE did not resolve the regression"
  },
  "DataSize": "~500 GB (estimated restore time: 45 minutes)"
}
```
