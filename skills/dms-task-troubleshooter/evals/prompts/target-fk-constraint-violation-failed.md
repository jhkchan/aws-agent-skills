# Eval prompt: target-fk-constraint-violation-failed

Diagnose the following DMS task failure and emit the standard VERDICT
block.

Task: arn:aws:dms:us-east-1:111111111111:task:TASK003
Source engine: oracle (RDS Oracle 19c)
Target engine: postgres (Aurora PostgreSQL 15)
Migration type: full-load-and-cdc
Instance: dms.r5.2xlarge

```json
{
  "TaskStatus": "failed",
  "FailedTable": "ORDERS",
  "ORDERS_FullLoadRowCount": 0,
  "OtherTablesLoaded": "successfully",
  "TaskLogs": {
    "ERROR": "insert or update on table 'orders' violates foreign key constraint 'orders_customer_id_fkey'"
  },
  "TableStatistics": {
    "CUSTOMERS": "loading",
    "ORDERS": "attempted inserts (failed)"
  },
  "Checks": {
    "source_connection": "OK",
    "target_connection": "OK",
    "data_types_compatible": true
  }
}
```
