# Eval prompt: memory-pressure-cdc-stall

Diagnose the following DMS instance capacity issue affecting 3 CDC
tasks and emit the standard VERDICT block.

Instance: dms.r5.large (rep-inst-001)
Tasks: TASK004 (mysql->postgres), TASK005 (mysql->postgres),
TASK006 (oracle->postgres) — all CDC, all slow

```json
{
  "AllTasks": {
    "CDCLatencyTarget": "climbing on all 3 tasks",
    "TaskStatus": "running but applying changes slowly"
  },
  "CloudWatch last hour": {
    "FreeableMemory": "avg 200MB, min 50MB",
    "SwapUsage": "avg 2GB, climbing",
    "CPUUtilization": "avg 85%",
    "CDCChangesDiskSource": "non-zero on all 3 tasks"
  },
  "SourceCDCConfigs": "all verified OK (binlog_format=ROW, wal_level=logical, LogMiner configured)",
  "SourceTargetSGs": "all OK"
}
```
