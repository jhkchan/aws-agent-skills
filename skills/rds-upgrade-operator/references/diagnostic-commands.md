# Diagnostic and Pre-flight Commands — RDS and Aurora Engine Upgrade Operator


## Pre-flight: database metadata gate — live-account commands

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
