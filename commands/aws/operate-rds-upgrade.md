---
description: Operate AWS RDS and Aurora engine upgrade workflows — major version upgrade, minor version upgrade, blue/green deploy for zero-downtime, parameter and option group migration, global database upgrade sequencing, maintenance window scheduling, post-upgrade verification, and rollback via PITR — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
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
routes_to: rds-upgrade-operator
---

# /aws:operate-rds-upgrade

Activate the `rds-upgrade-operator` skill and plan/execute an RDS or
Aurora engine upgrade operation with deterministic pre-checks, CONFIRM
gate, and post-verification.

## What it does

Reads a database/cluster configuration plus the intended operation and
applies the priority-ordered pre-check sequence:

1. Pre-flight database metadata gate — short-circuit unavailable
   instances, pending modifications, and conflicting maintenance
   actions.
2. Pre-check gate — REVIEW_REQUIRED if any check needs human attention
   (missing parameter group for target family, application driver
   incompatibility, global database sequencing, insufficient storage
   headroom, blue/green cutover timing).
3. OPERATION_COMPLETED or REVIEW_REQUIRED — emit the exact CLI sequence
   with all flags populated, the expected side-effects (EngineVersion
   changes, instance reboots, replicas rebuild), and the CONFIRM gate
   prompt.
4. Execute behind CONFIRM gate — capture pre-state snapshot, execute
   the CLI, monitor upgrade progress via RDS events.
5. Post-verification — EngineVersion matches target, instance/cluster
   returned to available, application connectivity validated, no query
   regression above threshold. OPERATION_COMPLETED only if ALL post-
   verification checks pass.

Emits a deterministic VERDICT per operation:

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
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <rollback plan, monitoring, caveats>
```

## When to invoke

Paste a database/cluster configuration plus the intended operation, or
just describe the scenario and ask any of:

- "upgrade this RDS instance to the latest version"
- "upgrade Aurora MySQL from 5.7 to 8.0"
- "set up a blue/green deployment for zero downtime"
- "migrate the parameter group for PostgreSQL 14"
- "upgrade a global database across Regions"
- "rollback the upgrade via point-in-time recovery"
- "verify query performance after the upgrade"

A bare DB instance ID + any upgrade verb ("upgrade this database",
"major version upgrade") also routes here via the orchestrator.

## Inputs

- Database/cluster configuration (`describe-db-instances` or
  `describe-db-clusters` JSON): `Status`, `Engine`, `EngineVersion`,
  `DBInstanceClass`, `MultiAZ`, `PendingModifiedValues`,
  `AutoMinorVersionUpgrade`, `PreferredMaintenanceWindow`,
  `DBParameterGroups`, `OptionGroupMemberships`.
- Engine version validity (`describe-db-engine-versions`): target
  version is a valid upgrade target from the current version.
- Parameter group compatibility: a custom parameter group for the
  target engine family exists.
- Option group compatibility: an option group for the target engine
  family exists.
- For global clusters: `describe-global-clusters` topology.
- For blue/green: blue/green deployment status and switchover plan.
- Application driver version (for compatibility verification).

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[REVIEW]` per check and the specific
  item to review.
- For OPERATION_COMPLETED: POST_VERIFY list with `[PASS]` per check,
  the new EngineVersion, application connectivity verification,
  Performance Insights comparison, monitoring recommendations.
- For REVIEW_REQUIRED: the specific items requiring human review
  (missing parameter group, driver incompatibility, global sequencing,
  rollback plan, blue/green timing) and the remediation steps.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for RDS/Aurora engine upgrades).
- `/aws:operate-rds-snapshots` for the snapshot-side counterpart —
  creating pre-upgrade snapshots and PITR restore.
- `/aws:deploy-rds-instance` for the deploy-side counterpart —
  provisioning new RDS instances with the target engine version.
