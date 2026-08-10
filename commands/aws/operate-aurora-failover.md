---
description: Operate Aurora cluster failover and recovery — automatic Multi-AZ failover, planned failover to promote a specific replica, unplanned failover, failback, Aurora Global Database failover, RDS Proxy verification, endpoint behavior, DNS cache flush, and post-failover verification.
nl_triggers:
  - "Aurora failover"
  - "promote Aurora replica"
  - "planned failover Aurora"
  - "unplanned failover Aurora"
  - "failback Aurora cluster"
  - "Aurora Global Database failover"
  - "RDS Proxy failover"
  - "Aurora writer endpoint"
  - "Aurora reader endpoint"
  - "Aurora primary unreachable"
  - "Aurora Multi-AZ failover"
  - "verify Aurora failover"
  - "Aurora split-brain"
  - "Aurora DNS cache failover"
  - "Aurora connection string update"
  - "Aurora replica promotion"
routes_to: aurora-failover-operator
---

# /aws:operate-aurora-failover

Activate the `aurora-failover-operator` skill and plan/execute an Aurora
cluster failover with deterministic pre-checks, CONFIRM gate, and
post-verification.

## What it does

Reads a cluster configuration plus the intended failover operation and
applies the priority-ordered pre-check sequence:

1. Pre-flight cluster metadata gate — short-circuit `modifying`/`failing-over`
   states, Global DB writers, active Database Activity Streams.
2. Pre-check gate — BLOCKED if any check fails (no healthy reader, Global
   DB writer without managed failover, high replica lag, unhealthy RDS
   Proxy targets).
3. READY — emit the exact CLI sequence with all flags populated, endpoint
   behavior (writer CNAME follows new primary, reader endpoint unchanged),
   DNS cache flush step, and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI, wait
   for the failover to complete.
5. Post-verification — cluster status, writer role verification, write
   connectivity test, replica lag convergence, RDS Proxy health, reader
   endpoint load-balancing. COMPLETED only if ALL post-verification checks
   pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <automatic | planned | unplanned | failback | global>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <cluster-id, writer-instance, target-replica>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
WRITER_ENDPOINT: <writer endpoint behavior>
READER_ENDPOINT: <reader endpoint behavior>
CONNECTION_NOTES: <DNS cache, RDS Proxy, connection string updates>
```

## When to invoke

Paste a cluster configuration plus the intended operation, or just
describe the scenario and ask any of:

- "failover our Aurora cluster"
- "promote a specific replica to writer"
- "failback to the original primary"
- "failover our Aurora Global Database"
- "verify our Aurora failover completed"
- "our Aurora primary is unreachable"
- "does RDS Proxy survive failover?"

A bare cluster-id + any failover verb also routes here via the orchestrator.

## Inputs

- Cluster configuration (`describe-db-clusters` JSON): status, engine,
  Multi-AZ, members (writer/reader roles, `IsClusterWriter`), Global DB
  membership, activity stream status.
- Per-instance details (`describe-db-instances` JSON): instance status, AZ,
  `AuroraReplicaLag`.
- The intended operation: `automatic`, `planned`, `unplanned`, `failback`,
  `global`.
- For planned failover: the target replica identifier to promote.
- For Global DB: the global cluster identifier and target secondary region.
- RDS Proxy configuration (if associated): proxy name, target group health.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for failure.
- For READY: the exact CLI sequence, expected duration, endpoint behavior,
  DNS cache flush step, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, writer/reader
  endpoint behavior, and connection notes.
- For BLOCKED: the specific failure reason and remediation guidance.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Operate specialist for Aurora failover and recovery).
- `/aws:operate-rds-backup-restore` for RDS/Aurora backup and restore
  operations (snapshots, PITR, backtrack) — complement failover with
  backup-based recovery.
- `/aws:audit-rds-instance` for the security/compliance posture of the
  Aurora cluster before/after failover.
