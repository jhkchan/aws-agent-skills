# Advanced Patterns — RDS and Aurora Engine Upgrade Operator


## Step 0: Expert knowledge — non-obvious RDS/Aurora upgrade behaviors

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
