---
description: Diagnose AWS DMS replication task failures — task status (stopped/failed), source connection (SG, credentials, binlog/pglogical/MS-CDC/LogMiner), target connection (IAM, PK/FK constraints), CDC latency (memory, disk), full load errors (table mapping, data type mismatch, LOB), and task settings optimization (Logging, validation) — with a symptom-to-root-cause diagnostic tree and verification probes.
nl_triggers:
  - "DMS task failed"
  - "DMS task stopped"
  - "DMS replication task error"
  - "DMS source connection failed"
  - "DMS target connection failed"
  - "DMS CDC latency"
  - "DMS CDC lag growing"
  - "DMS full load stuck"
  - "DMS table statistics zero rows"
  - "DMS binary logging disabled"
  - "DMS pglogical not installed"
  - "DMS wal_level logical"
  - "DMS constraint violation"
  - "DMS data type mismatch"
  - "DMS LOB size limit"
  - "DMS memory pressure"
  - "DMS disk swap"
  - "DMS Serverless"
  - "DMS Babelfish"
  - "DMS Fleet Advisor"
routes_to: dms-task-troubleshooter
---

# /aws:troubleshoot-dms-task

Activate the `dms-task-troubleshooter` skill and diagnose a DMS
replication task failure with a symptom-to-root-cause diagnostic tree
and verification probes.

## What it does

Reads a DMS task symptom (task status failed, CDC latency climbing,
full-load stuck, constraint violation) plus the task metadata and
applies the priority-ordered diagnostic tree:

1. Pre-flight task metadata gate — short-circuit malformed input,
   identify source engine and migration type, pull CloudWatch Logs.
2. Symptom-based routing — task-failed-at-start (Step 1), task-failed-
   mid-migration (Step 2), source connection (Step 3), source CDC
   config (Step 4), target connection/constraints (Step 5), CDC
   latency/capacity (Step 6), full-load/data errors (Step 7), task
   settings/IAM (Step 8).
3. ROOT_CAUSE_FOUND — emit the failing LAYER, the evidence (failing
   probe + passing probes), and the REMEDIATION with verification
   commands.
4. NEED_MORE_INFO — a probe requires operator input (task logs empty,
   source engine unknown, error message ambiguous).
5. ESCALATE — AWS-side DMS service incident (rare).

Emits a deterministic VERDICT per diagnosis:

```text
TARGET: <task-arn> (source: <engine>, target: <engine>, instance: <class>)
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <SOURCE_CONNECTION | SOURCE_BINARY_LOGGING | SOURCE_PERMISSIONS |
        TARGET_CONNECTION | TARGET_CONSTRAINTS | TARGET_PERMISSIONS |
        TASK_SETTINGS | TABLE_MAPPING | DATA_TYPE_MISMATCH | LOB_LIMIT |
        INSTANCE_CAPACITY | MEMORY_PRESSURE | DISK_SWAP | NETWORK_SG |
        IAM_ROLE | DMS_SERVICE | UNKNOWN>
EVIDENCE:
  - <observed symptom — task status, error message, metric anomaly>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <task-arn>/<endpoint>. Proceed?
  (yes/no)"
```

## When to invoke

Paste a DMS task symptom plus metadata, or just describe the scenario
and ask any of:

- "DMS task TASK001 failed on start"
- "the task logs say logical decoding requires wal_level >= logical"
- "CDC latency is climbing on my MySQL source"
- "the full load is stuck at table ORDERS with zero rows"
- "the target is throwing foreign key constraint violations"
- "all my DMS tasks are slow at the same time"
- "the task logs are empty — I can't see any errors"
- "binlog retention on my RDS MySQL source"
- "pglogical extension missing on my PostgreSQL source"
- "is it the instance or the task that's the bottleneck?"

A bare task ARN or ID + any failure symptom also routes here via the
orchestrator.

## Inputs

- Task configuration (`dms describe-replication-tasks` JSON): `Status`,
  `StopReason`, `LastFailureMessage`, `MigrationType`,
  `TableMappings`, `ReplicationTaskSettings`.
- Replication instance (`dms describe-replication-instances`): `Class`,
  `EngineVersion`, `AllocatedStorage`, `MultiAZ`.
- Endpoints (`dms describe-endpoints`): source/target `EngineName`,
  `ServerName`, `Port`, `SslMode`.
- Table statistics (`dms describe-table-statistics`): per-table
  `FullLoadRowCount`, `Inserts`/`Deletes`/`Updates`, `LastErrorMessage`.
- Task logs (`logs filter-log-events --log-group-name dms-task-<id>`):
  engine-specific error messages.
- CloudWatch metrics: `CDCLatencySource`, `CDCLatencyTarget`,
  `CDCChangesDiskSource`, `FreeableMemory`, `SwapUsage`,
  `CPUUtilization`.
- IAM roles: `dms-vpc-role`, `dms-cloudwatch-logs-role`.
- Source/target security groups: ingress rules.

## Outputs

- One VERDICT block per diagnosis.
- EVIDENCE list with the failing probe (confirms the cause) and passing
  probes (layers ruled out).
- For ROOT_CAUSE_FOUND: the REMEDIATION with exact CLI commands and
  verification steps, behind a CONFIRM gate.
- For NEED_MORE_INFO: the list of missing information and the next
  probe to run once the info is available.
- For ESCALATE: the AWS Health Dashboard link and Support case
  recommendation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for DMS replication tasks).
- `/aws:audit-rds-security-group` for auditing the source/target SG
  posture that may block DMS connectivity.
- `/aws:troubleshoot-alb-5xx` if the DMS API itself (behind an ALB) is
  returning 5xx — separate from task-level failures.
