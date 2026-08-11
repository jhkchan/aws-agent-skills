# Eval prompt: postgres-cdc-wal-level-failed

Diagnose the following DMS task failure and emit the standard VERDICT
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION,
CONFIRM).

Task: arn:aws:dms:us-east-1:111111111111:task:TASK001
Source engine: postgres (RDS PostgreSQL 15)
Target engine: postgres (Aurora PostgreSQL 15)
Migration type: full-load-and-cdc
Instance: dms.r5.large

```json
{
  "TaskStatus": "failed",
  "StopReason": "Task 'TASK001' was suspended.",
  "LastFailureMessage": "Task 'TASK001' was suspended.",
  "TaskLogs": {
    "ERROR": "logical decoding requires wal_level >= logical"
  },
  "SourceQuery": {
    "query": "select setting from pg_settings where name='wal_level';",
    "result": "replica"
  },
  "SourceChecks": {
    "pglogical_extension": "installed",
    "source_sg_allows_dms_sg_on_5432": true,
    "dms_user_has_replication_attribute": true
  }
}
```
