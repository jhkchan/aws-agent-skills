# Worked Examples — RDS and Aurora Engine Upgrade Operator


## Worked example — major-upgrade via blue/green (REVIEW_REQUIRED)

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

## Worked example — global database upgrade (condensed)

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

## Worked example — rollback via PITR (condensed)

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
