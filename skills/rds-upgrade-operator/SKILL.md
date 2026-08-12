---
name: rds-upgrade-operator
description: >-
  Operates Amazon RDS and Aurora engine upgrade workflows end-to-end — major
  version upgrades (explicit opt-in, pre-check: snapshot, parameter group
  compatibility, application driver support), minor version upgrades
  (auto-minor-version flag, patch schedule), Aurora MySQL 5.7 to 8.0,
  PostgreSQL 13 to 14 to 15 upgrade paths, blue/green deployments for zero-
  downtime upgrades, custom parameter group migration for the target engine
  version, option group migration, application connection string validation,
  post-upgrade verification (query performance regression, feature parity,
  analyzer changes), rollback strategy via point-in-time recovery, global
  database upgrade sequencing (primary then secondaries), multi-AZ upgrade
  behavior (rolling failover), and maintenance window scheduling. Runs
  deterministic pre-checks (available state, pending actions, snapshot
  exists, param group compatibility, option group compatibility, replication
  topology, storage type, free storage headroom) behind a CONFIRM gate and
  emits OPERATION_COMPLETED or REVIEW_REQUIRED per operation. Use when
  upgrading RDS or Aurora engine versions, planning a major version cut-over,
  configuring blue/green for zero downtime, migrating parameter groups across
  versions, sequencing a global database upgrade, or verifying post-upgrade
  query performance.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws rds modify-db-instance --engine-version, modify-db-cluster
  --engine-version, create-blue-green-deployment, switchover-blue-green-deployment,
  describe-db-engine-versions, describe-db-instances, describe-db-clusters,
  create-db-snapshot, describe-db-snapshots, modify-db-instance
  --auto-minor-version-upgrade, promote-read-replica, aws ec2 describe-security-groups
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - RDS upgrade
  - Aurora upgrade
  - major version upgrade
  - minor version upgrade
  - engine version
  - auto-minor-version-upgrade
  - Aurora MySQL 8.0
  - PostgreSQL 15
  - blue/green deployment
  - zero-downtime upgrade
  - parameter group migration
  - option group migration
  - connection string validation
  - post-upgrade verification
  - query performance regression
  - point-in-time recovery
  - rollback strategy
  - global database upgrade
  - multi-AZ upgrade
  - maintenance window
  - switchover
  - UpgradeInProgress
tags: [aws, rds, aurora, database, upgrade, mysql, postgresql, blue-green, operate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Databases
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "OPERATION_COMPLETED | REVIEW_REQUIRED"
  when_to_use: >-
    Upgrading an RDS instance or Aurora cluster engine version (major or
    minor), planning a major version cut-over with pre-checks and rollback,
    deploying blue/green for zero-downtime upgrade, migrating parameter or
    option groups to a target engine version, sequencing a global database
    upgrade across Regions, scheduling a maintenance-window upgrade, enabling
    or disabling auto-minor-version-upgrade, validating application connection
    strings after an upgrade, or verifying post-upgrade query performance and
    feature parity.
  activation_triggers:
    - "upgrade RDS engine"
    - "major version upgrade"
    - "minor version upgrade"
    - "Aurora MySQL 8.0 upgrade"
    - "PostgreSQL 15 upgrade"
    - "blue/green deploy RDS"
    - "zero-downtime database upgrade"
    - "parameter group migration"
    - "option group migration"
    - "global database upgrade"
    - "maintenance window upgrade"
    - "auto minor version upgrade"
    - "post-upgrade verification"
    - "rollback RDS upgrade"
    - "RDS engine version"
  invocation_schema: >-
    Input: either (a) a database/cluster configuration (describe-db-instances
    or describe-db-clusters output) plus the intended operation (major-upgrade,
    minor-upgrade, blue-green-upgrade, param-group-migrate, global-upgrade,
    configure-auto-minor, post-upgrade-verify, rollback), OR (b) a DB instance
    or cluster identifier + operation for live-account execution. Output:
    deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY /
    NOTES block per upgrade, where VERDICT is OPERATION_COMPLETED or
    REVIEW_REQUIRED.
---

# RDS and Aurora Engine Upgrade Operator

## What this skill does

Executes RDS and Aurora engine upgrade operations correctly and safely.
Runs deterministic pre-checks before any state-changing CLI (instance or
cluster is `available`, no pending maintenance actions, pre-upgrade
snapshot exists and is `available`, parameter group is compatible with the
target engine version, option group is compatible, replication topology
is understood, storage type and free-space headroom are sufficient),
executes the upgrade behind a CONFIRM gate, and verifies the result by
confirming `EngineVersion` matches the target, the instance or cluster
returns to `available`, application connectivity is validated, and no
query-performance regression exceeds the configured threshold. Every
major upgrade produces an explicit opt-in requirement plus a blue/green
recommendation for zero downtime; every minor upgrade surfaces the
`AutoMinorVersionUpgrade` flag so the operator knows whether the next
patch is automatic.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (REVIEW_REQUIRED/OPERATION_COMPLETED) + pre-check priority | Before any operation |
| **§ Mindset** | Why major upgrades need explicit opt-in, blue/green as the zero-downtime primitive, the param-group trap | Understanding the safety model |
| **§ Pre-flight** | Database/cluster metadata gate — state, pending actions, multi-AZ, global cluster, replicas | Before executing any CLI |
| **§ Process** | Per-operation planning: major, minor, blue-green, param-group, global, auto-minor, verify, rollback | When choosing which operation to run |
| **§ Output format** | Structured OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that cause extended downtime or strand a cluster mid-upgrade | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, snapshot, application driver check, rollback plan | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `REVIEW_REQUIRED` | Operation plan is ready but requires human review before execution (major upgrade requires explicit opt-in, blue/green plan needs cutover timing approval, global database upgrade sequencing across Regions, PITR rollback plan, parameter group with `pending-reboot` changes that need a maintenance window) | Emit plan with the specific items to review, wait for operator approval |
| `OPERATION_COMPLETED` | Upgrade finished and post-verification passed (`EngineVersion` matches target, instance or cluster returned to `available`, application connectivity validated, no query regression above threshold, replicas in sync) | Emit verification results, monitoring plan |

**Priority order for pre-checks (apply in this sequence, any failure routes
to REVIEW_REQUIRED with the failure surfaced):**

1. **Database reachability** — instance or cluster exists, `DBInstanceStatus`
   or `Status` is `available`, NOT `modifying`, `upgrading`,
   `backing-up`, or `storage-optimization`. No `PendingModifiedValues`
   that would conflict with the upgrade.
2. **Target engine version validity** — `describe-db-engine-versions`
   confirms the target `EngineVersion` is valid for the instance class,
   storage type, and current engine. Major version path is supported
   (skipping major versions is not allowed).
3. **Pre-upgrade snapshot** — a manual snapshot exists taken AFTER any
   pending writes, with status `available`. This is the rollback anchor.
4. **Parameter group compatibility** — a custom parameter group exists for
   the target engine family (e.g., `default.aurora-mysql8.0` for an Aurora
   MySQL 5.7 to 8.0 upgrade). The default param group from the source
   version is NOT compatible.
5. **Option group compatibility** — an option group for the target engine
   family exists and includes the same options (or validated replacements).
6. **Replication topology understood** — read replicas, Aurora replicas,
   and global cluster secondaries are identified. The upgrade order is
   primary then replicas (or blue/green switchover).
7. **Storage headroom** — at least 20% free storage for the upgrade
   temporary space (engine upgrade can rebuild system tables).
8. **Application driver support** — the application's database driver
   version supports the target engine version (e.g., MySQL Connector/J 8.x
   for Aurora MySQL 8.0; PostgreSQL JDBC 42.x for PostgreSQL 15).
9. **Maintenance window** — the upgrade is scheduled in the configured
   maintenance window OR the operator has explicitly approved an immediate
   upgrade.

**Cost/time baselines (2026):**

- Minor version upgrade: 5-20 minutes of `upgrading` state, brief
  connection drop on single-AZ; multi-AZ rolls through a failover.
- Major version upgrade: 20 minutes to 4 hours depending on database
  size (system table rebuild). Aurora is typically faster than RDS
  Standard because Aurora stores the system catalogs differently.
- Blue/green switchover: typically under 60 seconds (DNS shift). The
  green environment provisioning takes 30-90 minutes before the
  switchover.
- Global database upgrade: primary Region first (20 min to 4 hours),
  then each secondary Region sequentially (the secondary rebuilds from
  the upgraded primary).
- PITR rollback to pre-upgrade state: recovery time objective is the
  snapshot-or-PITR-restore time (minutes to hours depending on size).

## Mindset

**One-line takeaway:** a major version upgrade is an irreversible
cut-over unless you pre-planned a rollback path (PITR to the pre-upgrade
moment or a blue/green switchover back). `modify-db-instance
--engine-version` returns immediately but the engine upgrade runs
asynchronously — the database is in `upgrading` state for the full
duration, during which the old version is gone and the new version is
not yet ready. Driven by three RDS realities:

- **Major upgrades require explicit opt-in; auto applies only minor.**
  `AutoMinorVersionUpgrade: true` schedules minor version patches in the
  maintenance window. It NEVER triggers a major version upgrade. Setting
  `--engine-version` to a higher major version is the explicit opt-in
  and it is irreversible without a restore — you cannot "downgrade" an
  engine in place.

- **Blue/green deploy provides zero-downtime upgrade.** The blue/green
  pattern creates a full copy of the production environment (the green)
  running the target engine version, keeps it in sync via logical
  replication, and switches traffic over via a DNS shift (typically
  under 60 seconds). This is the recommended path for production major
  upgrades. The switchover is reversible until the green is deleted.

- **Parameter group must be compatible with the target version.** Each
  engine family has its own parameter group family (e.g.,
  `aurora-mysql5.7` vs `aurora-mysql8.0`). An upgrade from 5.7 to 8.0
  REQUIRES a parameter group from the `aurora-mysql8.0` family. Using
  the 5.7 parameter group causes the upgrade to fail or the instance to
  boot with default parameters, silently dropping custom settings like
  `max_connections`, `innodb_buffer_pool_size`, or `character_set_server`.

## Pre-flight: database metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `describe-db-instances` paginates at 100/page — drain
`--starting-token` to completion.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws rds describe-db-instances --db-instance-identifier <id>` —
   capture `DBInstanceStatus`, `Engine`, `EngineVersion`,
   `DBInstanceClass`, `MultiAZ`, `PendingModifiedValues`,
   `AutoMinorVersionUpgrade`, `DBParameterGroups`,
   `OptionGroupMemberships`, `StorageType`.
2. `aws rds describe-db-clusters --db-cluster-identifier <id>` — for
   Aurora; capture `Status`, `EngineVersion`, `DBClusterMembers`,
   `GlobalClusterIdentifier`, `DBClusterParameterGroup`.
3. `aws rds describe-db-engine-versions --engine <engine>
   --db-instance-class <class>` — confirm the target is a valid
   upgrade target. Check `SupportsGlobalDatabases` for global clusters.
4. `aws rds describe-db-snapshots --db-instance-identifier <id>
   --snapshot-type manual` — confirm pre-upgrade snapshot is `available`.
5. `aws rds describe-pending-maintenance-actions` — confirm no
   conflicting pending action.
6. `aws rds describe-global-clusters --global-cluster-identifier <id>`
   — if a global cluster member, capture primary and secondaries.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: DB/cluster configuration
is not valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws rds describe-db-instances
--db-instance-identifier <id> --output json and re-plan.`

| Database attribute | Effect on operation |
|---|---|
| `DBInstanceStatus` not `available` | Upgrade BLOCKED. Wait for the current operation to finish, or investigate a stuck status. |
| `PendingModifiedValues` non-empty | Upgrade routes to REVIEW_REQUIRED. Resolve the pending change (apply immediately or cancel) before scheduling the upgrade. |
| `MultiAZ: true` | Upgrade runs through a rolling failover. Plan for two brief connection drops (primary -> standby, then upgrade -> failback). |
| `ReadReplicaSourceDBInstanceIdentifier` set (this is a replica) | Upgrade the SOURCE first, then replicas. Replicas cannot run a higher engine version than the source. |
| `GlobalClusterIdentifier` set | Global cluster member. Primary Region must upgrade first, then secondaries. Use the global-upgrade operation. |
| `StorageType: gp2` with < 20% free | Upgrade routes to REVIEW_REQUIRED — increase storage or convert to gp3 first. |
| `AutoMinorVersionUpgrade: true` | Minor versions are applied automatically in the maintenance window. A manual minor upgrade overrides the schedule. |
| `DBParameterGroups[0].ParameterApplyStatus: pending-reboot` | A pending parameter change will be applied during the upgrade reboot. Route to REVIEW_REQUIRED. |
| `DBParameterGroups[0].DBParameterGroupName: default.<engine><version>` | Default param group. For major upgrades, a custom param group for the target version is required. |
| `OptionGroupMemberships[0].Status: pending-maintenance` | An option group change is pending. Resolve before upgrade. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious RDS/Aurora upgrade behaviors

These behaviors are easy to misjudge without operational upgrade
experience. Each changes a plan if ignored:

- **Major upgrades are NEVER automatic.** `AutoMinorVersionUpgrade`
  only schedules patches within the same major version. A major version
  bump requires explicit `modify-db-instance --engine-version <target>`.
  You cannot skip major versions (PostgreSQL 13 to 15 requires 14
  first; Aurora MySQL 5.6 to 8.0 requires 5.7 first). Use
  `describe-db-engine-versions` to enumerate valid upgrade targets.

- **Parameter group families are engine-version-specific.** Aurora
  MySQL 5.7 uses `aurora-mysql5.7`; upgrading to 8.0 requires an
  `aurora-mysql8.0` group. The upgrade does NOT auto-migrate parameters
  — pre-create the target group, diff, apply custom values, attach
  during upgrade. Same for option groups (e.g., MEMCACHED removed in
  Aurora MySQL 8.0).

- **Blue/green deploy is the zero-downtime path.** RDS provisions a
  staging environment (green) at the target version, syncs via logical
  replication, and switches via DNS shift (under 60 seconds). The green
  is retained as a rollback safety net. Use for production major
  upgrades instead of in-place.

- **Multi-AZ upgrades roll through a failover.** Standby upgraded
  first, then failover, then old primary upgraded — TWO brief
  connection drops. Read replicas must match or trail the source
  version; upgrade source first. Global database upgrades are Region-
  sequential (primary first, secondaries rebuilt; secondaries
  unavailable during rebuild).

- **`--apply-immediately` vs maintenance window.** Without
  `--apply-immediately`, the upgrade is deferred to the next
  `PreferredMaintenanceWindow`. The upgrade reboots the database — all
  connections dropped, in-flight transactions rolled back. Pending
  parameter/option group changes (`pending-reboot`) are applied.

- **MySQL 8.0 `caching_sha2_password`.** The default auth plugin
  changed. Applications using `mysql_native_password` need a driver
  upgrade OR the parameter group override
  `default_authentication_plugin = mysql_native_password`.

- **PostgreSQL 14+ default changes.** `default_statistics_target`
  increased to 1000; `shared_preload_libraries` handling tightened.
  `pg_upgrade` rebuilds planner statistics — run `ANALYZE` on all
  tables post-upgrade to prevent query plan regressions.

- **Aurora Serverless v1 does NOT support in-place major upgrades.**
  Restore a snapshot to a Serverless v2 cluster instead.

- **`SupportsGlobalDatabases` flag.** Verify the target engine version
  supports global databases before planning a global cluster upgrade.

- **`upgrade-failed` is a terminal state if auto-rollback is unclean.**
  Recovery is PITR restore to the pre-upgrade snapshot — which is why
  a named manual snapshot (taken when the DB is `available` and
  quiesced) is mandatory. Enable `PerformanceInsightsEnabled` before
  the upgrade to capture the pre-upgrade query-latency baseline.

### Step 1: Pre-check gate — REVIEW_REQUIRED if any check needs human attention

Run ALL pre-checks for the chosen operation. If any check fails or
requires human review, the verdict is REVIEW_REQUIRED with the specific
items listed. Do NOT execute until the operator reviews.

**For ALL operations:**
1. Instance or cluster exists (`describe-db-instances` /
   `describe-db-clusters` does not return
   `DBInstanceNotFound`).
2. `DBInstanceStatus` / `Status` is `available` (not `modifying`,
   `upgrading`, `backing-up`, `storage-optimization`, `resetting`,
   `incompatible-parameters`).
3. No `PendingModifiedValues` (a pending change conflicts with the
   upgrade — apply or cancel first).
4. Storage type and free space: at least 20% free storage. For `gp2`,
   consider converting to `gp3` first (gp3 supports higher IOPS at
   lower cost and is the recommended storage type for 2024+).
5. `PerformanceInsightsEnabled: true` (for before/after comparison).

**For major-upgrade (`modify-db-instance --engine-version
<target-major>`):**
6. `describe-db-engine-versions` confirms the target version is a
   valid upgrade target from the current version.
7. The upgrade path is sequential (no skipped major versions).
8. A custom parameter group for the target engine family exists and
   is attached (or will be attached as part of the modify call).
9. An option group for the target engine family exists and is attached
   (or will be attached as part of the modify call).
10. A pre-upgrade manual snapshot exists and is `available`.
11. Application driver support verified (driver version supports the
    target engine version).
12. `PreferredMaintenanceWindow` acknowledged — with
    `--apply-immediately` the upgrade starts now; without it, the
    upgrade is deferred to the next window.
13. Blue/green recommended for production (surface the alternative
    plan if the operator chose in-place).

**For minor-upgrade (`modify-db-instance --engine-version
<target-minor>` or `--auto-minor-version-upgrade`):**
6. `describe-db-engine-versions` confirms the target version is valid.
7. Minor version is within the same major version.
8. `AutoMinorVersionUpgrade` current state acknowledged — if `true`
   and the target minor is the current preferred patch, the upgrade
   may happen automatically in the next window.

**For blue-green-upgrade (`create-blue-green-deployment`):**
6. The source instance or cluster is `available`.
7. The target engine version is a valid upgrade target.
8. Parameter and option groups for the target version are identified.
9. The application tolerates logical replication lag during the sync
   phase (typically seconds; longer for large write-heavy workloads).
10. A switchover window is planned (the switchover itself is under 60
    seconds but the green provisioning takes 30-90 minutes).

**For param-group-migrate (pre-stage a target-version parameter group):**
6. The target parameter group family matches the target engine family
   (e.g., `aurora-mysql8.0` for Aurora MySQL 8.0).
7. Parameters diffed against the source param group; custom values
   reproduced.
8. Static parameters (those requiring a reboot) identified — they will
   apply at the next reboot (i.e., during the upgrade).

**For global-upgrade (multi-Region global cluster):**
6. `describe-global-clusters` confirms the global cluster topology.
7. The primary Region is identified.
8. Each secondary Region's cluster is `available`.
9. The target engine version has `SupportsGlobalDatabases: true`.
10. A Region-by-Region cutover plan is documented (primary first,
    secondaries rebuilt sequentially).

**For configure-auto-minor (toggle `AutoMinorVersionUpgrade`):**
6. The operator understands that enabling auto-minor schedules patches
   in the maintenance window — it does NOT trigger an immediate patch.

**For post-upgrade-verify (read-only):**
6. The instance or cluster has returned to `available`.
7. `EngineVersion` matches the target.
8. Performance Insights has data for the pre-upgrade and post-upgrade
   windows.

**For rollback (PITR to pre-upgrade state):**
6. A pre-upgrade snapshot or a valid PITR window (within the backup
   retention period) exists.
7. The operator understands that rollback means a NEW instance or
   cluster — the endpoint changes. Application connection strings
   must be updated.

**Upgrade failure-mode table (use during diagnosis):**

| Symptom | Root cause | Fix |
|---|---|---|
| Upgrade fails immediately with `InvalidParameterCombination` | Target engine version not valid for the instance class or storage type | Check `describe-db-engine-versions --engine <engine> --db-instance-class <class>` for valid targets |
| Upgrade fails with `ParameterGroupNotFound` | No parameter group for the target engine family attached | Create a target-family param group and attach via `--db-parameter-group-name` |
| Upgrade fails with `OptionGroupNotFound` | No option group for the target engine family attached | Create a target-family option group and attach via `--option-group-name` |
| Instance stuck in `upgrade-failed` | Incompatible parameter or option, or insufficient storage | Review CloudWatch Logs and RDS events; the instance attempts auto-rollback. If stuck, PITR restore. |
| Application cannot connect after MySQL 8.0 upgrade | `caching_sha2_password` default not supported by old driver | Update driver, OR set `default_authentication_plugin = mysql_native_password` in the target param group |
| Application cannot connect after PostgreSQL upgrade | `pg_hba.conf` changes in the new version (stricter defaults) | Update the target param group `pg_hba.conf` entries; verify application IP ranges |
| Query performance regression after PostgreSQL upgrade | Planner statistics stale after `pg_upgrade` | Run `ANALYZE` on all tables; consider `VACUUM ANALYZE` for heavily updated tables |
| Aurora replicas lag after cluster upgrade | Replicas rebuilding from the upgraded writer | Monitor `AuroraReplicaLag`; wait for it to return to baseline |
| Global cluster secondary unreachable during upgrade | Secondary is being rebuilt from the upgraded primary | Plan for secondary Region downtime; consider a read traffic cutover before the upgrade |

### Step 2: OPERATION_COMPLETED or REVIEW_REQUIRED — emit operation plan

If all pre-checks pass AND the operation is read-only or low-risk
(minor version with `--apply-immediately`, parameter group migration
without static changes, post-upgrade verification), emit
`VERDICT: OPERATION_COMPLETED` (for already-finished operations) or
the executable plan with the CONFIRM gate.

For operations requiring human review (major upgrade, blue/green
cutover, global database sequencing, rollback via PITR), emit
`VERDICT: REVIEW_REQUIRED` with the specific items to review. The plan
includes:

- The exact AWS CLI command with all flags populated from the database
  configuration.
- The expected duration (minor 5-20 min; major 20 min to 4 hours;
  blue/green switchover under 60 seconds after 30-90 min of green
  provisioning).
- The expected side-effects (`EngineVersion` changes, instance reboots,
  connections drop, replicas rebuild).
- The CONFIRM gate prompt.
- The rollback plan (snapshot ARN for in-place; blue/green switchback
  for blue/green).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`modify-db-instance`, `modify-db-cluster`,
  `create-blue-green-deployment`, `switchover-blue-green-deployment`,
  `delete-blue-green-deployment`, `promote-read-replica`,
  `restore-db-instance-to-point-in-time`), emit:
  `CONFIRM: About to <operation> on <db-id> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`.
  Do NOT execute until the operator confirms.
- Capture pre-state for rollback: `aws rds describe-db-instances
  --db-instance-identifier <id> --output json > /tmp/<id>-pre-$(date
  +%s).json` AND a manual snapshot if one does not already exist:
  `aws rds create-db-snapshot --db-instance-identifier <id>
  --db-snapshot-id <id>-pre-upgrade-$(date +%s)`.
- Execute the CLI. For `modify-db-instance`, the API returns
  immediately; the actual upgrade runs asynchronously. The instance
  enters `upgrading` state.
- Monitor the upgrade via RDS events:
  `aws rds describe-events --source-type db-instance
  --source-identifier <id> --start-time $(($(date +%s) - 600))000`.

### Step 4: Post-verification — OPERATION_COMPLETED

After the upgrade finishes, run post-verification. ALL checks must pass
for `OPERATION_COMPLETED`.

1. `describe-db-instances --db-instance-identifier <id>` — confirm
   `EngineVersion` matches the target AND `DBInstanceStatus: available`.
2. `describe-db-snapshots` — confirm the automatic snapshot taken by RDS
   during the upgrade is `available` (this is the post-upgrade backup).
3. For multi-AZ: confirm both the primary and standby are on the target
   version (check `SecondaryAvailabilityZone` and failover status).
4. For Aurora clusters: confirm ALL cluster members (writer and readers)
   report the target `EngineVersion`. Check `AuroraReplicaLag` has
   returned to baseline.
5. For global clusters: confirm ALL secondary Region clusters have been
   rebuilt and report the target version.
6. Application connectivity: test a connection from the application's
   subnet/SG to the database endpoint on the DB port. Verify the
   application driver version connects successfully.
7. Query performance verification: compare Performance Insights
   top-queries latency (post-upgrade) against the pre-upgrade baseline.
   Investigate any query with > 2x latency regression.
8. For PostgreSQL: run `ANALYZE` on all user databases to refresh
   planner statistics. Schedule a `VACUUM ANALYZE` during the next low-
   traffic window.
9. For MySQL/Aurora MySQL 8.0: verify the authentication plugin
   (`caching_sha2_password` vs `mysql_native_password`) matches what
   the application driver expects.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim OPERATION_COMPLETED. A failed verification
typically means a query regression or an application connectivity
issue; route to the rollback operation if the regression is severe.

## Output format (per operation)

```text
OPERATION: <major-upgrade | minor-upgrade | blue-green-upgrade | param-group-migrate | global-upgrade | configure-auto-minor | post-upgrade-verify | rollback>
VERDICT: OPERATION_COMPLETED | REVIEW_REQUIRED
TARGET: <db-id-or-cluster-id> (engine: <current-version> -> <target-version>)
PRE_CHECKS:
  - [PASS] <check description>
  - [REVIEW] <check description> — <item to review>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <rollback plan, monitoring, caveats>
```

### Worked example — minor-upgrade (in-place, OPERATION_COMPLETED)

```text
OPERATION: minor-upgrade
VERDICT: OPERATION_COMPLETED
TARGET: prod-orders-db (engine: postgres 14.10 -> 14.11)
PRE_CHECKS:
  - [PASS] DBInstanceStatus: available
  - [PASS] No PendingModifiedValues
  - [PASS] describe-db-engine-versions confirms 14.11 is valid for
    aurora-postgresql on db.r6g.large
  - [PASS] Storage: 800 GB allocated, 350 GB free (44% headroom)
  - [PASS] PerformanceInsightsEnabled: true
  - [PASS] AutoMinorVersionUpgrade: false (operator-initiated)
STEPS:
  1. CONFIRM: About to upgrade prod-orders-db from PostgreSQL 14.10 to
     14.11 in account 111111111111 region us-east-1. This will reboot
     the instance (brief connection drop, ~30 seconds for single-AZ,
     two drops for multi-AZ). Proceed? (yes/no)
  2. aws rds create-db-snapshot \
       --db-instance-identifier prod-orders-db \
       --db-snapshot-id prod-orders-db-pre-14-11-$(date +%s)
  3. aws rds wait db-snapshot-available \
       --db-snapshot-id prod-orders-db-pre-14-11-...
  4. aws rds modify-db-instance \
       --db-instance-identifier prod-orders-db \
       --engine-version 14.11 \
       --apply-immediately
  5. aws rds wait db-instance-available \
       --db-instance-identifier prod-orders-db
POST_VERIFY:
  - [PASS] EngineVersion: 14.11 (confirmed via describe-db-instances)
  - [PASS] DBInstanceStatus: available
  - [PASS] Application connectivity: psql connect from app subnet OK
  - [PASS] Performance Insights: top-10 query latency within +/- 10%
    of pre-upgrade baseline
NOTES:
  - Minor version upgrade completed in 12 minutes. Single-AZ, one
    connection drop of ~25 seconds.
  - PostgreSQL ANALYZE scheduled for the next low-traffic window
    (03:00 UTC) to refresh planner statistics.
  - Rollback: restore from snapshot prod-orders-db-pre-14-11-...
    if any regression is detected. This creates a NEW instance —
    endpoint will change.
```

### Worked example — major-upgrade via blue/green (REVIEW_REQUIRED)

```text
OPERATION: blue-green-upgrade
VERDICT: REVIEW_REQUIRED
TARGET: prod-payments-cluster (engine: aurora-mysql 5.7.mysql_aurora.2.11.4 -> 8.0.mysql_aurora.3.04.0)
PRE_CHECKS:
  - [PASS] DBClusterStatus: available
  - [PASS] describe-db-engine-versions confirms 8.0 target is valid
  - [PASS] Target parameter group aurora-mysql8.0-payments-custom
    exists (diffed against source, 12 custom params reproduced)
  - [PASS] Target option group aurora-mysql8.0-payments-opts exists
    (MEMCACHED option removed — not supported in 8.0)
  - [PASS] Pre-upgrade snapshot prod-payments-pre-8-0 available
  - [REVIEW] Application driver: MySQL Connector/J 5.1.49 — does NOT
    support caching_sha2_password. Review: upgrade driver to 8.0.x OR
    set default_authentication_plugin=mysql_native_password in the
    target param group.
  - [REVIEW] Blue/green provisioning window: 45-90 minutes. The green
    cluster will be created and kept in sync via logical replication.
    Confirm the switchover window (03:00 UTC Sunday).
  - [REVIEW] Rollback plan: after switchover, the blue (old 5.7)
    environment is kept for 72 hours as a rollback safety net. Confirm
    the deletion schedule.
STEPS:
  1. CONFIRM: About to create a blue/green deployment for
     prod-payments-cluster, upgrading Aurora MySQL 5.7 to 8.0. The
     green environment will be provisioned over 45-90 minutes, then
     held for a scheduled switchover. Proceed? (yes/no)
  2. aws rds create-blue-green-deployment \
       --blue-green-deployment-name prod-payments-bg-8-0 \
       --source arn:aws:rds:us-east-1:111111111111:cluster:prod-payments-cluster \
       --target-engine-version 8.0.mysql_aurora.3.04.0 \
       --delete-automated-backups false
  3. aws rds wait blue-green-deployment-provisioning-complete \
       --blue-green-deployment-id <bg-id>
  4. (Scheduled switchover at 03:00 UTC Sunday)
     aws rds switchover-blue-green-deployment \
       --blue-green-deployment-id <bg-id>
  5. aws rds wait blue-green-deployment-switchover-complete \
       --blue-green-deployment-id <bg-id>
POST_VERIFY:
  - (pending switchover)
  - [PASS] EngineVersion: 8.0.mysql_aurora.3.04.0 (post-switchover)
  - [PASS] All cluster members report 8.0
  - [PASS] Application connectivity with Connector/J 8.0.x: OK
  - [PASS] Performance Insights: AAS and top-query latency within
    +/- 15% of baseline
NOTES:
  - Blue/green switchover is under 60 seconds (DNS shift). The green
    (8.0) becomes the new production; the blue (5.7) is retained for
    72 hours as rollback.
  - Rollback: switchover back to blue if any issue is detected within
    72 hours. After 72 hours, the blue is deleted and rollback requires
    a PITR restore.
  - MEMCACHED option was removed (not supported in Aurora MySQL 8.0).
    Confirm no application dependency on Memcached via the RDS endpoint.
```

### Worked example — global database upgrade (condensed)

```text
OPERATION: global-upgrade
VERDICT: REVIEW_REQUIRED
TARGET: global-payments-cluster (aurora-mysql 5.7 -> 8.0,
        primary: us-east-1, secondaries: eu-west-1, ap-southeast-1)
PRE_CHECKS:
  - [PASS] Global topology: primary us-east-1, 2 secondaries
  - [PASS] All clusters Status: available; SupportsGlobalDatabases: true
  - [PASS] Target param group exists in all 3 Regions
  - [REVIEW] Sequencing: primary first, secondaries rebuilt sequentially.
    Each secondary rebuild: 2-6h. Total window: up to 18h. Confirm.
  - [REVIEW] Secondary downtime during rebuild — plan read failover.
  - [REVIEW] Rollback = PITR primary + re-create secondaries (multi-hour).
STEPS:
  1. CONFIRM: upgrade global-payments-cluster primary (us-east-1),
     secondaries rebuilt after. Total up to 18h. Proceed? (yes/no)
  2. aws rds modify-db-cluster --db-cluster-identifier prod-payments-cluster \
       --engine-version 8.0.mysql_aurora.3.04.0 \
       --db-cluster-parameter-group-name aurora-mysql8.0-global-payments \
       --apply-immediately --region us-east-1
  3. aws rds wait db-cluster-available --db-cluster-identifier \
       prod-payments-cluster --region us-east-1
  4. RDS auto-rebuilds secondaries. Monitor via describe-global-clusters.
POST_VERIFY: (pending) — all clusters EngineVersion 8.0, lag < 1s.
NOTES: Secondaries unavailable during rebuild. Rollback = multi-hour PITR.
```

### Worked example — rollback via PITR (condensed)

```text
OPERATION: rollback
VERDICT: REVIEW_REQUIRED
TARGET: prod-orders-db (rollback from PG 15.4 to pre-upgrade 14.11)
PRE_CHECKS:
  - [PASS] Pre-upgrade snapshot prod-orders-db-pre-15-4 available
  - [PASS] PITR window 2026-08-04 02:50 UTC within 35-day retention
  - [REVIEW] Rollback creates NEW instance — endpoint changes.
    Application connection strings must be updated. Confirm plan.
  - [REVIEW] Data loss: writes between PITR timestamp and now are lost.
    Confirm timestamp is correct.
  - [REVIEW] Restore time ~45min for 500 GB. Confirm downtime tolerance.
STEPS:
  1. CONFIRM: restore prod-orders-db to 2026-08-04T02:50:00Z. Creates
     NEW instance prod-orders-db-rollback. Proceed? (yes/no)
  2. aws rds restore-db-instance-to-point-in-time \
       --source-db-instance-identifier prod-orders-db \
       --target-db-instance-identifier prod-orders-db-rollback \
       --restore-time 2026-08-04T02:50:00Z \
       --db-parameter-group-name aurora-postgresql14-payments-custom
  3. aws rds wait db-instance-available \
       --db-instance-identifier prod-orders-db-rollback
  4. Cutover: update application connection strings.
POST_VERIFY: (pending) — EngineVersion 14.11, connectivity OK, data verified.
NOTES: Original upgraded instance still running — delete after rollback stable.
```

## Anti-Patterns — NEVER

- NEVER attempt a major version upgrade without a pre-upgrade manual
  snapshot. The automatic snapshot RDS takes is harder to locate under
  incident pressure. A named manual snapshot is the rollback anchor.

- NEVER attach a parameter group from the wrong engine family. Aurora
  MySQL 5.7 param groups are NOT compatible with 8.0 — the instance
  will boot with defaults, silently dropping custom settings.

- NEVER skip major versions in an upgrade path. PostgreSQL 13 to 15
  requires going through 14. Aurora MySQL 5.6 to 8.0 requires 5.7
  first. `describe-db-engine-versions` lists valid targets.

- NEVER upgrade a read replica before its source, or a global cluster
  secondary before the primary. Always upgrade source/primary first.

- NEVER assume `AutoMinorVersionUpgrade: true` handles major versions.
  It only applies to minor patches within the same major. Major
  upgrades always require explicit opt-in.

- NEVER run an in-place major upgrade on production without considering
  blue/green deploy first. In-place upgrades have a 20-minute to 4-hour
  `upgrading` window. Blue/green provides a sub-60-second switchover
  with a rollback safety net.

- NEVER delete the blue environment immediately after a blue/green
  switchover. Keep it 24-72 hours as a rollback safety net.

- NEVER forget to run `ANALYZE` after a PostgreSQL major upgrade.
  `pg_upgrade` rebuilds planner statistics; without `ANALYZE`, query
  plans can be 10-100x slower.

- NEVER assume the application driver supports the target version.
  MySQL 8.0's `caching_sha2_password` breaks older connectors.
  PostgreSQL 14+ tightened `pg_hba.conf` defaults. Verify BEFORE.

- NEVER rely on "downgrade" as rollback. RDS does not support in-place
  engine downgrades. The ONLY rollback is PITR/snapshot restore —
  which creates a NEW instance with a NEW endpoint.

- NEVER ignore `PendingModifiedValues`. A pending storage, instance
  class, or parameter change that fires during the upgrade causes
  unpredictable behavior. Resolve before upgrading.

- NEVER upgrade Aurora Serverless v1 in-place to a major version —
  restore a snapshot to Serverless v2 instead.

- NEVER auto-execute a state-changing RDS CLI without the CONFIRM gate.
  Engine upgrades, blue/green switchovers, and PITR restores have
  downtime and data-loss side effects.

- NEVER overlook `SupportsGlobalDatabases` when upgrading a global
  cluster member. Not all engine versions support global databases.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`modify-db-instance`, `modify-db-cluster`,
  `create-blue-green-deployment`, `switchover-blue-green-deployment`,
  `restore-db-instance-to-point-in-time`, `promote-read-replica`,
  `delete-db-instance`), emit: `CONFIRM: About to <operation> on
  <target> in account <account> region <region>. This will
  <consequence>. Proceed? (yes/no)`.

- **Capture pre-state for rollback.** Before any upgrade:
  `aws rds describe-db-instances --db-instance-identifier <id>
  --output json > /tmp/<id>-pre-$(date +%s).json` AND take a manual
  snapshot. Wait for `available` before starting.

- **Verify engine version validity.** `describe-db-engine-versions`
  confirms the target is a valid upgrade target. Verify parameter and
  option group compatibility (target-family groups exist). Verify
  application driver support (MySQL 8.0 `caching_sha2_password`,
  PostgreSQL 14+ `pg_hba.conf`).

- **Prefer blue/green over in-place for production major upgrades.**
  Blue/green provides a sub-60-second switchover with a rollback
  safety net. In-place upgrades have a 20-min to 4-hour window with
  no rollback path short of PITR restore. Verify replication topology
  (source/primary first, then replicas/secondaries).

## Recent AWS features (2024-2026)

- **Blue/Green Deployments GA (2023-2024):** Creates a full staging
  environment (green) at the target engine version, kept in sync via
  logical replication. Switchover via DNS shift (under 60 seconds).
  The recommended path for production major upgrades.

- **Aurora MySQL 3.x (MySQL 8.0):** Default auth plugin changed to
  `caching_sha2_password`. MEMCACHED option removed. Applications
  using `mysql_native_password` need a driver upgrade or parameter
  override.

- **PostgreSQL 15 on RDS/Aurora:** `MERGE` statement, improved
  `VACUUM`, `default_statistics_target` increased to 1000.

- **gp3 storage:** Recommended over gp2 — higher IOPS at lower cost.
  Consider migrating before upgrading (independent of engine upgrade).

- **Aurora Serverless v2:** Supports MySQL 8.0 and PostgreSQL 14+.
  Serverless v1 does NOT support in-place major upgrades — restore
  snapshot to v2.

- **Global Database sequencing:** Region-sequential (primary first,
  secondaries rebuilt). `SupportsGlobalDatabases` flag on
  `describe-db-engine-versions` validates target version.

- **RDS Extended Support (2024-2025):** Run a major version past
  community EOL for a premium — a bridge, not a substitute for
  upgrading.

- **Performance Insights long-term retention (730 days):** Enable
  before upgrade to preserve the pre-upgrade baseline for comparison.

## Domain

AWS CloudOps / RDS and Aurora Engine Upgrade, Major Version Cut-over &
Zero-Downtime Blue/Green Deploy.

## AWS documentation

- **Amazon RDS User Guide** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html
- **Upgrading a DB instance engine version** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_UpgradeDBInstance.Upgrading.html
- **Major version upgrades** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_UpgradeDBInstance.MajorVersionUpgrade.html
- **Minor version upgrades** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_UpgradeDBInstance.MinorVersionUpgrade.html
- **Blue/Green Deployments** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/blue-green-deployments.html
- **Aurora MySQL upgrade paths** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Updates.Upgrades.html
- **Aurora PostgreSQL upgrade paths** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.Updates.Upgrades.html
- **Global database upgrades** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database-upgrade.html
- **RDS API Reference** — https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/
- **Point-in-time recovery** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html
