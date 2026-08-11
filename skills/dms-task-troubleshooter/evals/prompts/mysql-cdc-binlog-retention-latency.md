# Eval prompt: mysql-cdc-binlog-retention-latency

Diagnose the following DMS task latency issue and emit the standard
VERDICT block.

Task: arn:aws:dms:us-east-1:111111111111:task:TASK002
Source engine: mysql (RDS MySQL 8.0)
Target engine: postgres (Aurora PostgreSQL 15)
Migration type: full-load-and-cdc
Instance: dms.r5.xlarge

```json
{
  "TaskStatus": "running",
  "CDCLatencySource": "86400s (24h, climbing)",
  "CDCLatencyTarget": "5s (normal)",
  "SourceQueries": {
    "binlog_format": "ROW",
    "binlog_row_image": "FULL",
    "binlog_retention_hours": "0",
    "show_binary_logs": "only the current binlog (older binlogs purged)"
  },
  "SourceChecks": {
    "dms_user_has_replication_slave": true,
    "dms_user_has_replication_client": true,
    "source_sg_allows_dms_sg_on_3306": true
  }
}
```
