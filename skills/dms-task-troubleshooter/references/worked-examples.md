# DMS Task Troubleshooter — worked examples (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Worked example — CDC latency from binlog retention (MySQL RDS) (moved from SKILL.md)


```text
TARGET: arn:aws:dms:us-east-1:111:task:TASK002 (source: mysql,
        target: postgres, instance: dms.r5.xlarge)
VERDICT: ROOT_CAUSE_FOUND
REASON: MySQL RDS source has binlog_retention_hours=0 (default),
  causing binlogs to be purged before DMS reads them. CDCLatencySource
  climbed to 86400s (24h); task cannot recover the missing changes.
LAYER: SOURCE_BINARY_LOGGING
EVIDENCE:
  - Symptom: CDCLatencySource climbing steadily over 24 hours; task
    running but not applying changes.
  - Probe: show variables like 'binlog_retention_hours'; returns 0.
  - Probe: show binary logs; returns only current binlog — older
    binlogs purged.
  - Passing: binlog_format=ROW; binlog_row_image=FULL; DMS user has
    REPLICATION SLAVE, REPLICATION CLIENT.
REMEDIATION:
  1. aws rds modify-db-parameter-group --db-parameter-group-name
     <pg-name> --parameters ParameterName=binlog_retention_hours,
     ApplyMethod=immediate,ParameterValue=24
  2. For already-purged binlogs: reload from snapshot or accept data
     loss for the gap. Restart in full-load-and-cdc mode if needed.
  3. Verify binlog_retention_hours=24; monitor CDCLatencySource.
CONFIRM: "About to set binlog_retention_hours=24 on <pg-name>. No
  reboot required. Proceed? (yes/no)"
```


## Worked example — FK constraint violation on full load (moved from SKILL.md)


```text
TARGET: arn:aws:dms:us-east-1:111:task:TASK003 (source: oracle,
        target: postgres, instance: dms.r5.2xlarge)
VERDICT: ROOT_CAUSE_FOUND
REASON: Target PostgreSQL has FK constraint on orders.customer_id
  referencing customers.id, but customers was not loaded before
  orders. FK check failed on first orders insert.
LAYER: TARGET_CONSTRAINTS
EVIDENCE:
  - Symptom: task failed at table ORDERS, FullLoadRowCount at 0 while
    other tables loaded.
  - Probe: task logs: "insert or update on table 'orders' violates
    foreign key constraint 'orders_customer_id_fkey'."
  - Probe: describe-table-statistics shows CUSTOMERS in "loading"
    while ORDERS attempted inserts — load order did not respect FK.
  - Passing: source/target connections OK; data types compatible.
REMEDIATION:
  1. On target: set session_replication_role=replica; (disables FK
     checks for the session).
  2. Or set DMS TargetTablePrepMode=TRUNCATE_BEFORE_LOAD with table-
     order rules placing parent tables before child tables.
  3. aws dms start-replication-task --replication-task-arn <task-arn>
     --start-replication-task-type reload-target
  4. Verify: ORDERS FullLoadRowCount advancing; no constraint errors.
CONFIRM: "About to disable FK checks on the target and restart the
  task. Proceed? (yes/no)"
```


## Worked example — memory pressure causing CDC stall (moved from SKILL.md)


```text
TARGET: arn:aws:dms:us-east-1:111:task:TASK004 (source: mysql,
        target: postgres, instance: dms.r5.large)
VERDICT: ROOT_CAUSE_FOUND
REASON: dms.r5.large (8GB RAM) running 3 CDC tasks. FreeableMemory
  dropped to 200MB, SwapUsage climbed to 2GB, causing thrashing and
  CDC disk spill.
LAYER: MEMORY_PRESSURE
EVIDENCE:
  - Symptom: CDCLatencyTarget climbing on all 3 tasks; task running
    but applying changes slowly.
  - Probe: CloudWatch FreeableMemory: avg 200MB, min 50MB (under
    500MB threshold for dms.r5.large).
  - Probe: SwapUsage: avg 2GB, climbing. CDCChangesDiskSource non-zero.
  - Passing: source binlog retention sufficient; SG rules OK; target
    constraints OK.
REMEDIATION:
  1. aws dms modify-replication-instance --replication-instance-arn
     <inst-arn> --replication-instance-class dms.r5.xlarge
     --apply-immediately
  2. Or move 1-2 tasks to a separate instance to reduce contention.
  3. Verify: FreeableMemory > 2GB; SwapUsage drops to zero;
     CDCLatencyTarget decreases on all tasks.
CONFIRM: "About to upgrade <inst-id> dms.r5.large -> dms.r5.xlarge.
  Brief task interruption. Proceed? (yes/no)"
```

