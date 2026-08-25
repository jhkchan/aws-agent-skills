---
name: dynamodb-global-tables-operator
description: 'Operates DynamoDB Global Tables safely across the full lifecycle: creating replicated tables in multiple regions, managing replication configuration, adding and removing replica regions, monitoring ReplicationLatency and ReplicaLag, executing application-level regional failover, and managing per-region PITR. Runs deterministic pre-checks (table ACTIVE in all regions, same key schema, PITR consistent, IAM permissions, no in-progress updates) before any state-changing CLI, executes the operation behind a CONFIRM gate, and verifies the result. Covers Global Tables v2 (standard, single-writer), LAST_WRITER_WINS conflict resolution, and per-region PITR enablement. Emits a verdict (READY | BLOCKED | COMPLETED) per operation with the exact CLI sequence, expected side-effects, and verification commands. Use when creating a global table, adding or removing replica regions, monitoring cross-region replication latency, failing over to another region, or managing per-region continuous backups.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws dynamodb create-global-table, update-global-table, describe-global-table, describe-global-table-settings, describe-table, update-table, describe-continuous-backups, aws cloudwatch get-metric-statistics for AWS/DynamoDB metrics, and aws application-autoscaling describe-scaling-policies (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: dynamodb, databases, global-tables, multi-region, replication, operate, failover
  dependencies: aws-orchestrator
  keywords: DynamoDB, Global Tables, Global Tables v2, multi-region, replication, replica, ReplicationLatency, ReplicaLag, conflict resolution, LAST_WRITER_WINS, LWW, regional failover, application-level failover, add replica, remove replica, PITR, per-region PITR, continuous backups, cross-region, disaster recovery
  when_to_use: Creating a DynamoDB Global Table replicated across multiple regions, adding a new replica region to an existing global table, removing a replica region, monitoring cross-region replication latency, failing over application traffic to a different region, enabling or verifying per-region PITR on a global table, or planning a multi-region disaster recovery drill.
  when_not_to_use: DynamoDB table configuration posture audits (use dynamodb-table- auditor), single-region backup/restore operations (use dynamodb- backup-operator), IAM policy authoring for fine-grained access control, or DynamoDB throttling diagnosis (use dynamodb-throttling- troubleshooter). This skill operates global table replication; it does not audit table posture or diagnose throttling.
  activation_triggers: create DynamoDB Global Table, add replica region DynamoDB, remove replica region DynamoDB, DynamoDB multi-region replication, DynamoDB Global Tables failover, DynamoDB replication latency, DynamoDB ReplicationLatency high, DynamoDB Global Tables v2, DynamoDB LAST_WRITER_WINS, enable PITR global table, DynamoDB cross-region replication, DynamoDB disaster recovery multi-region, operate DynamoDB Global Tables
  invocation_schema: 'Input: either (a) a DynamoDB table configuration with the intended operation (create-global-table, add-replica, remove-replica, failover, enable-pitr, verify-replication), OR (b) a table-name + operation for live-account execution. Output: deterministic OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
---

# DynamoDB Global Tables Operator

## What this skill does

Executes DynamoDB Global Tables operations correctly and safely across
the full lifecycle: creating replicated tables, adding/removing replica
regions, monitoring replication latency, executing application-level
regional failover, and managing per-region PITR. Runs deterministic
pre-checks before any state-changing CLI, executes behind a CONFIRM
gate, and verifies the result.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority order | Before any operation |
| **STRICT output contract** | Mandatory output block format | Before emitting any response |
| **Mindset** | Global Tables v2 model, LWW conflict resolution, the failover asymmetry | Understanding the replication model |
| **Expert heuristic** | Non-obvious global table behaviours from operational experience | Review before complex operations |
| **Process** | Per-operation planning: create, add-replica, remove-replica, failover, PITR | When choosing which operation to run |
| **NEVER** | Top 5 anti-patterns that cause data loss or replication gaps | Review before risky operations |
| **Recent AWS features** | 2024-2026 Global Tables updates | Reference for latest capabilities |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (table not ACTIVE in all regions, schema mismatch, PITR inconsistent, replica CREATING/DELETING, IAM permission missing, table in UPDATING) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Operation finished and post-verification passed (all replicas ACTIVE, ReplicationLatency within threshold, PITR enabled per region) | Emit replica status, verification results, notes |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **Table status** — must be `ACTIVE` in ALL regions. `CREATING`,
   `UPDATING`, `DELETING` in any region → BLOCKED.
2. **Schema consistency** — all replicas must share identical key
   schema, attribute definitions, billing mode, and table class.
3. **Replication status** — for add/remove, no replica in `CREATING`
   or `DELETING` state. Check `describe-global-table`.
4. **PITR consistency** — for failover and DR operations, PITR should
   be enabled on all replicas. For per-region PITR enablement, verify
   the target region's current PITR status.
5. **IAM permissions** — caller needs `dynamodb:CreateGlobalTable`,
   `dynamodb:UpdateGlobalTable`, `dynamodb:DescribeGlobalTable` on the
   table ARN in the primary region. Cross-region operations need
   permissions in each region.
6. **Conflict resolution awareness** — Global Tables v2 uses
   `LAST_WRITER_WINS` exclusively. Concurrent writes to different
   regions may conflict. Verify the application tolerates LWW.

**Cost/latency baselines (2026):**

- Cross-region replication latency: typically under 1 second for most
  region pairs (depends on geographic distance).
- Replica creation time: minutes to hours depending on table size
  (data is copied from an existing replica to the new region).
- Global Tables replicated write cost: 2x+ the single-region WCU cost
  (one WCU per replica region per write).
- PITR cost per region: ~$0.20/GB-month for continuous-backup storage,
  charged independently per replica region.

## STRICT output contract

Every operation response MUST emit this block. No prose before the
block; the block is the entire actionable output.

```text
OPERATION: <create-global-table | add-replica | remove-replica | failover | enable-pitr | verify-replication>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <table name, primary region, replica regions>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait/poll command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
REPLICA_STATUS:
  - <region>: <ACTIVE | CREATING | DELETING | UPDATING>
NOTES: <application cutover steps, cost implications, cleanup, caveats>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <operation> on <table> in <regions>.
  Proceed? (yes/no)"
```

Do NOT omit any field. If a field is not applicable, write `N/A` with a
one-line reason.

## Mindset

**One-line takeaway:** DynamoDB Global Tables v2 provides active-active
multi-region replication with `LAST_WRITER_WINS` conflict resolution.
There is no automatic failover — failover is application-level (point
the client to a different region). Every replica is independently
queryable and writable. Per-region PITR is independent.

Driven by four Global Tables realities:

- **Global Tables v2 is the standard (2019+).** The original Global
  Tables (v1, via `aws dynamodb_streams`) is deprecated. All new global
  tables use the v2 model: `create-global-table` with replication
  group members, managed internally by DynamoDB. Operators who follow
  v1 documentation will use the wrong APIs.

- **Conflict resolution is LAST_WRITER_WINS, always.** When the same
  item is written concurrently in two regions, the write with the
  later timestamp wins. There is no conflict detection or resolution
  callback. The application must be designed for LWW: either avoid
  concurrent writes to the same item from different regions, use
  region-specific partition keys, or accept that the last writer wins.
  This is the single most important design constraint.

- **Failover is application-level, not service-level.** DynamoDB does
  not automatically route traffic to a healthy region during a
  regional outage. The application (or SDK with `RegionSwitchingRetryPolicy`)
  must detect the failure and redirect writes/reads to another region.
  The writer endpoint does NOT follow a primary — every region is a
  primary. Plan the failover mechanism before you need it.

- **Each replica region is independently configured for PITR, billing
  mode, autoscaling, and backups.** Enabling PITR on one replica does
  NOT enable it on others. Autoscaling policies must be registered per
  replica region. IAM resource policies must include all regional
  ARNs. This is the most common gap in global table operations.

## Expert heuristic — non-obvious global table behaviours

All ten non-obvious behaviours (replica bootstrapping, irreversible removal, per-region GSI/billing changes, dual describe views, per-pair ReplicationLatency, LWW thrashing, PITR restore creating a single-region table, per-replica autoscaling, linear WCU scaling) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when reviewing complex operations.

## Pre-flight: global table metadata gate

Run before any operation. Misclassifying these produces wrong plans.

Live-account pre-flight CLI (describe-global-table, per-region describe-table, describe-continuous-backups, ReplicationLatency and autoscaling metrics, in-progress update check) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before any live-account operation.

| Table attribute | Effect on operation |
|---|---|
| `TableStatus: ACTIVE` (all replicas) | Pre-check passes for all operations |
| `TableStatus: CREATING` (new replica) | BLOCKED for add/remove — wait for ACTIVE |
| `TableStatus: UPDATING` (any replica) | BLOCKED — wait for ACTIVE |
| `ReplicaStatus: ACTIVE` (all replicas) | Replication healthy; operations allowed |
| `ReplicaStatus: CREATING` (new replica) | BLOCKED for further replica changes |
| `ReplicaStatus: DELETING` (removed replica) | BLOCKED — wait for deletion to complete |
| `BillingMode` mismatch across replicas | BLOCKED — billing mode must be consistent |
| `PITRStatus: ENABLED` (region) | PITR available for that region's restore window |
| `PITRStatus: DISABLED` (region) | No continuous backup for that region |
| Key schema mismatch across replicas | BLOCKED — all replicas must have identical schema |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Global Tables behaviors

All eight Step 0 expert behaviors (empty-table prerequisite for create-global-table, update-global-table auto-creating replicas, name matching, LWW-only conflict resolution, async replication, per-region PITR, last-replica removal, describe-global-table-settings) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when planning any operation.

### Step 1: Pre-check gate — BLOCKED if any check fails

**For ALL operations:**
1. All existing replicas are `ACTIVE` (`describe-global-table`).
2. No replica is in `CREATING` or `DELETING` state.
3. The caller holds the required DynamoDB permissions.

**For create-global-table:**
4. Identical empty tables exist in all target regions with the same key
   schema, attribute definitions, and billing mode.
5. `describe-global-table` returns `GlobalTableNotFoundException` (the
   global table does not already exist).
6. PITR is either enabled or disabled consistently across all regions
   (recommend enabled).

**For add-replica:**
4. The target region does NOT already have a replica.
5. The global table exists with at least one ACTIVE replica.
6. The caller has `dynamodb:UpdateGlobalTable` and
   `dynamodb:CreateTable` in the target region.

**For remove-replica:**
4. The target region has an ACTIVE replica.
5. At least one replica will remain after removal (do not remove the
   last replica unless intentionally converting to single-region).
6. No application traffic is routing to the region being removed
   (verify via CloudWatch `ConsumedReadCapacityUnits` and
   `ConsumedWriteCapacityUnits` for that region).

**For failover:**
4. The target region has an ACTIVE replica.
5. `ReplicationLatency` to the target region is within acceptable
   bounds (< 1 second typical).
6. The application has a failover mechanism (SDK retry policy, Route 53
   health check, or manual DNS switch).

**For enable-pitr:**
4. The target region's table is ACTIVE.
5. `describe-continuous-backups` shows
   `PointInTimeRecoveryStatus: DISABLED` (or verify ENABLED if checking).

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated.
- The expected duration (replica creation: minutes to hours; replica
  removal: minutes; PITR enablement: seconds).
- The expected side-effects (new replica region for add-replica, table
  deleted in removed region for remove-replica).
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI, emit
  the CONFIRM prompt and wait for operator approval.
- Capture pre-state for audit.
- Execute the CLI. Capture the response.
- For long-running operations (add-replica), poll the replica status
  via `describe-global-table` until `ReplicaStatus: ACTIVE`.

### Step 4: Post-verification — COMPLETED

After the operation finishes, run post-verification. ALL checks must
pass for `COMPLETED`.

1. `describe-global-table` — all replicas show `ReplicaStatus: ACTIVE`.
2. `describe-table` per region — `TableStatus: ACTIVE` in all regions.
3. CloudWatch `ReplicationLatency` — within threshold (< 1s average).
4. For add-replica: verify data is replicating by writing a test item
   in one region and reading it in the new replica.
5. For remove-replica: verify the table is deleted in the removed
   region (`describe-table` returns `ResourceNotFoundException`).
6. For enable-pitr: verify `PointInTimeRecoveryStatus: ENABLED` via
   `describe-continuous-backups`.
7. For failover: verify the application is successfully reading and
   writing in the new primary region.

## Output format (per operation)

See STRICT output contract above. Worked examples below.

### Worked example — add replica region (READY)

```text
OPERATION: add-replica
VERDICT: READY
TARGET: orders-prod global table, adding replica in eu-west-1
  Current replicas: us-east-1, us-west-2
  Target replicas: us-east-1, us-west-2, eu-west-1
PRE_CHECKS:
  - [PASS] Global table orders-prod exists
  - [PASS] All current replicas ACTIVE (us-east-1: ACTIVE, us-west-2: ACTIVE)
  - [PASS] No replica in CREATING or DELETING state
  - [PASS] Target region eu-west-1 does not have an existing replica
  - [PASS] Caller IAM role has dynamodb:UpdateGlobalTable
  - [PASS] Caller IAM role has dynamodb:CreateTable in eu-west-1
  - [WARN] PITR is ENABLED in us-east-1 and us-west-2 — enable in
    eu-west-1 after replica creation
STEPS:
  1. CONFIRM: About to add replica region eu-west-1 to global table
     orders-prod. This will create a new table in eu-west-1 and copy
     data from an existing replica. Estimated time: 15-30 minutes for
     ~50 GB. Proceed? (yes/no)
  2. aws dynamodb update-global-table \
       --global-table-name orders-prod \
       --replica-updates '[{"Create":{"RegionName":"eu-west-1"}}]'
  3. Poll: aws dynamodb describe-global-table \
       --global-table-name orders-prod \
       --query 'GlobalTableDescription.ReplicationGroup[?RegionName==`eu-west-1`].ReplicaStatus'
     Wait for ACTIVE.
  4. Enable PITR in eu-west-1:
      aws dynamodb update-continuous-backups \
        --table-name orders-prod --region eu-west-1 \
        --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
  5. Register autoscaling in eu-west-1 (if PROVISIONED mode):
      aws application-autoscaling register-scalable-target \
        --service-namespace dynamodb \
        --resource-id table/orders-prod \
        --scalable-dimension dynamodb:table:WriteCapacityUnits \
        --min-capacity <min> --max-capacity <max> --region eu-west-1
POST_VERIFY:
  - (pending execution)
REPLICA_STATUS:
  - us-east-1: ACTIVE
  - us-west-2: ACTIVE
  - eu-west-1: CREATING (will transition to ACTIVE)
NOTES:
  - The new replica is read-only during CREATING. Writes will replicate
    to it automatically once ACTIVE.
  - PITR is NOT automatically enabled in eu-west-1 — step 4 is required.
  - Autoscaling policies are NOT automatically created in eu-west-1 —
    step 5 is required (PROVISIONED mode only).
  - Replicated write cost increases: each write now consumes 3x WCU
    (3 replicas) instead of 2x.
  - ReplicationLatency for eu-west-1 may be higher than us-west-2
    (geographic distance from us-east-1).
```

### Worked example — remove replica blocked by active traffic

Remove-replica BLOCKED worked example (active-traffic pre-check failure, redirect-first notes) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when planning a remove-replica operation.

### Worked example — regional failover (COMPLETED)

Regional failover COMPLETED worked example (SDK RegionSwitchingRetryPolicy cutover, LWW conflict notes, do-not-remove-degraded-replica) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when planning a failover or DR drill.

## Diagnostic command reference

All eight diagnostic commands (global table status, settings, regional status, PITR, ReplicationLatency, consumed capacity, list-global-tables, autoscaling) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when diagnosing replication or replica state.

## Anti-Patterns — NEVER (top 5)

- **NEVER remove a replica region without verifying it has no active
  application traffic.** Removing a replica deletes the table and all
  data in that region. If the application is still routing traffic
  there, it will fail immediately. Always check CloudWatch
  `ConsumedReadCapacityUnits` and `ConsumedWriteCapacityUnits` for the
  region before removal — they must be near-zero.

- **NEVER assume DynamoDB Global Tables has automatic failover.**
  DynamoDB does NOT redirect traffic during a regional outage. Failover
  is 100% application-level. The application (SDK retry policy, Route 53
  health check, or manual switch) must detect the failure and redirect
  to another region. Without a failover mechanism, the application will
  fail until the region recovers.

- **NEVER assume PITR, autoscaling, or IAM policies are replicated
  across regions.** Each replica region is independently configured.
  Enabling PITR in us-east-1 does NOT enable it in eu-west-1. Always
  configure PITR, autoscaling, and IAM per-region after adding a replica.

- **NEVER write concurrently to the same item from multiple regions
  without LWW-aware design.** Global Tables v2 uses LAST_WRITER_WINS
  exclusively. Concurrent writes to the same partition key from
  different regions will overwrite each other in a non-deterministic
  order (based on timestamp). Use region-specific keys, or
  DynamoDB Streams for merge, or accept LWW semantics.

- **NEVER assume schema changes propagate automatically.** Adding a
  GSI to one replica does NOT create it on other replicas. Billing
  mode changes, table class changes, and TTL configuration must each
  be applied region by region. Always plan schema changes as a
  per-region operation.

## Remediation guidance

Per-operation remediation sequences (create-global-table, add-replica, remove-replica, failover, enable-pitr) moved verbatim to [references/global-tables-procedures.md](references/global-tables-procedures.md).
Load on demand when executing any operation end-to-end.

## Recent AWS features (2024-2026)

Recent AWS features 2024-2026 (v2-only APIs, per-region PITR, ReplicationLatency metrics, cost attribution, strong-consistency preview, DeleteProtectionEnabled) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when deciding between v2 capabilities.

## References

See `references/global-tables-procedures.md` for the full operation
procedures (create, add-replica, remove-replica, failover, PITR), and
`references/multi-region-dr-guide.md` for the disaster recovery
planning guide including failover runbooks and RTO/RPO analysis.

## References (load on demand)

- [`references/advanced-patterns.md`](references/advanced-patterns.md) — expert heuristics, Step 0 expert behaviors, and recent AWS features (2024-2026) moved from SKILL.md
- [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — pre-flight and diagnostic command listings moved from SKILL.md
- [`references/worked-examples.md`](references/worked-examples.md) — the remove-replica (BLOCKED) and regional failover (COMPLETED) worked examples moved from SKILL.md; the add-replica (READY) example stays inline
- [`references/global-tables-procedures.md`](references/global-tables-procedures.md) — per-operation remediation sequences moved from SKILL.md, plus the pre-existing full operation procedures

## Domain

AWS CloudOps / DynamoDB Global Tables Multi-Region Replication and
Disaster Recovery.

## AWS documentation

- **DynamoDB Global Tables** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html
- **Global Tables v2** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/globaltables.V2.html
- **Multi-region resilience** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.bestpractices.html
- **DynamoDB Continuous Backups (PITR)** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.html
- **DynamoDB CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/dynamodb/
