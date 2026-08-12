# RDS and Aurora Upgrade Diagnostic Procedures Reference

Load this reference when diagnosing a failed or problematic RDS or Aurora
engine upgrade. The procedures below are the canonical sequences for each
symptom archetype, with the read-only diagnostic commands and the CLI to
fix each root cause.

## Decision tree — which diagnostic archetype

| Symptom | Use | Why |
|---|---|---|
| Upgrade failed immediately, `InvalidParameterCombination` | **Invalid target** | Target version not valid for the instance class or storage type |
| Upgrade failed with `ParameterGroupNotFound` | **Param group gap** | No parameter group for the target engine family |
| Instance stuck in `upgrade-failed` | **Stuck upgrade** | Incompatible parameter or option; auto-rollback may be in progress |
| Application cannot connect after MySQL 8.0 upgrade | **Auth plugin** | `caching_sha2_password` not supported by the application driver |
| Query performance regression after PostgreSQL upgrade | **Planner stats** | `pg_upgrade` rebuilt statistics; `ANALYZE` needed |
| Aurora replicas lag after cluster upgrade | **Replica rebuild** | Replicas rebuilding from the upgraded writer |
| Global cluster secondary unreachable | **Secondary rebuild** | Secondary being rebuilt from the upgraded primary |
| Upgrade completed but `EngineVersion` still shows old version | **Deferred upgrade** | `--apply-immediately` was not set; upgrade deferred to next maintenance window |

## Procedure: Invalid target version

**Symptom:** `modify-db-instance --engine-version <target>` fails
immediately with `InvalidParameterCombination` or
`InvalidDBInstanceModification`.

**Diagnostics:**

```bash
# 1. Check valid upgrade targets for the current version
aws rds describe-db-engine-versions \
  --engine aurora-mysql \
  --db-instance-class db.r6g.large \
  --query 'DBEngineVersions[?EngineVersion==`5.7.mysql_aurora.2.11.4`].ValidUpgradeTarget'

# 2. Verify the instance class and storage type are supported
aws rds describe-db-instances \
  --db-instance-identifier <id> \
  --query 'DBInstances[0].{Class:DBInstanceClass,Storage:StorageType,Engine:Engine,Version:EngineVersion}'
```

**Common findings:**

| Finding | Fix |
|---|---|
| Target version not in `ValidUpgradeTarget` list | Choose a valid target from the list; do not skip major versions |
| Instance class not supported for the target version | Modify the instance class first, then upgrade |
| Storage type `standard` (magnetic) not supported | Convert to `gp2` or `gp3` before upgrading |

## Procedure: Parameter group gap

**Symptom:** Upgrade fails with `ParameterGroupNotFound` or
`InvalidParameterCombination` mentioning a parameter group.

**Diagnostics:**

```bash
# 1. Check the current parameter group and its family
aws rds describe-db-instances \
  --db-instance-identifier <id> \
  --query 'DBInstances[0].DBParameterGroups'

# 2. List parameter groups for the target engine family
aws rds describe-db-parameter-groups \
  --query 'DBParameterGroups[?contains(DBParameterGroupFamily, `aurora-mysql8.0`)]'

# 3. For Aurora clusters, check the cluster-level parameter group
aws rds describe-db-clusters \
  --db-cluster-identifier <id> \
  --query 'DBClusters[0].DBClusterParameterGroup'
```

**Fix:**

```bash
# Create a custom parameter group for the target family
aws rds create-db-parameter-group \
  --db-parameter-group-name aurora-mysql8.0-custom \
  --db-parameter-group-family aurora-mysql8.0 \
  --description "Custom params for Aurora MySQL 8.0"

# Copy parameters from the source group (diff and apply)
aws rds describe-db-parameters \
  --db-parameter-group-name aurora-mysql5.7-custom \
  --source DBParameterGroupDefault > /tmp/source-params.json
# ... diff and apply custom parameters ...

# Attach the new parameter group during the upgrade
aws rds modify-db-instance \
  --db-instance-identifier <id> \
  --engine-version 8.0.mysql_aurora.3.04.0 \
  --db-parameter-group-name aurora-mysql8.0-custom \
  --apply-immediately
```

## Procedure: Stuck upgrade (instance in `upgrade-failed`)

**Symptom:** Instance status is `upgrade-failed`. RDS is attempting
auto-rollback.

**Diagnostics:**

```bash
# 1. Check the instance status and pending modifications
aws rds describe-db-instances \
  --db-instance-identifier <id> \
  --query 'DBInstances[0].{Status:DBInstanceStatus,
    Pending:PendingModifiedValues,Engine:Engine,Version:EngineVersion}'

# 2. Check RDS events for the failure reason
aws rds describe-events \
  --source-type db-instance \
  --source-identifier <id> \
  --duration 360 \
  --event-categories failure

# 3. Check CloudWatch Logs for engine-specific errors
aws logs tail RDSOSMetrics --since 1h
```

**Common findings and actions:**

| Finding | Action |
|---|---|
| `InvalidParameterValue` on a custom parameter | Remove or fix the parameter in the target param group; retry |
| Insufficient storage | Increase allocated storage; retry |
| Auto-rollback in progress | Wait for rollback to complete; the instance returns to `available` on the old version |
| Auto-rollback failed | PITR restore to the pre-upgrade snapshot |

## Procedure: MySQL 8.0 authentication plugin issue

**Symptom:** Upgrade to MySQL 8.0 succeeded but the application cannot
authenticate. Error: `Unable to load authentication plugin
'caching_sha2_password'`.

**Diagnostics:**

```bash
# Check the current default authentication plugin
aws rds describe-db-parameters \
  --db-parameter-group-name <target-pg> \
  --query 'Parameters[?ParameterName==`default_authentication_plugin`]'
```

**Fix option 1 — set the parameter (no downtime):**

```bash
aws rds modify-db-parameter-group \
  --db-parameter-group-name aurora-mysql8.0-custom \
  --parameters "ParameterName=default_authentication_plugin,ParameterValue=mysql_native_password,ApplyMethod=immediate"
```

Wait for the parameter to apply (dynamic parameter — no reboot needed).

**Fix option 2 — upgrade the application driver:**

Update the MySQL Connector/J (or equivalent) to version 8.0.x, which
supports `caching_sha2_password`.

## Procedure: PostgreSQL planner statistics regression

**Symptom:** After a PostgreSQL major upgrade, top queries show 5-50x
latency increase. Execution plans changed.

**Diagnostics:**

```bash
# 1. Compare Performance Insights top-query latency before and after
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier <db-id> \
  --metric-queries '[{Metric:{"Dimensions":{"db.sql.tokenized":["top"]}},GroupBy:{Type:"dimension",Key:"db.sql.tokenized"}}]' \
  --start-time <pre-upgrade> \
  --end-time <post-upgrade>

# 2. Check if ANALYZE has been run
psql -c "SELECT relname, last_analyze, last_autoanalyze FROM pg_stat_user_tables ORDER BY last_analyze DESC NULLS LAST LIMIT 20;"
```

**Fix:**

```bash
# Run ANALYZE on all user databases to refresh planner statistics
psql -d <dbname> -c "ANALYZE;"

# For heavily updated tables, run VACUUM ANALYZE
psql -d <dbname> -c "VACUUM ANALYZE <table>;"

# Schedule a recurring ANALYZE during low-traffic windows
# (pg_cron or an EventBridge + Lambda job)
```

## Procedure: Aurora replica lag after cluster upgrade

**Symptom:** After `modify-db-cluster --engine-version`, the writer
upgraded successfully but replicas show high `AuroraReplicaLag`.

**Diagnostics:**

```bash
# 1. Check replica lag
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name AuroraReplicaLag \
  --dimensions Name=DBClusterIdentifier,Value=<cluster-id> \
  --start-time $(date -u -v-2h +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 --statistics Average,Maximum

# 2. Check all cluster members' engine versions
aws rds describe-db-clusters \
  --db-cluster-identifier <id> \
  --query 'DBClusters[0].DBClusterMembers[*].{Instance:DBInstanceIdentifier,Role:IsClusterWriter,Status:DBClusterInstanceStatus}'
```

**Expected behavior:** Replica lag spikes during the rolling upgrade
(writer upgraded first, then readers rebuild). Lag should return to
under 100 ms within 10-30 minutes. If lag persists, check for long-
running queries on the writer blocking the replication stream.

## Procedure: Global cluster secondary unreachable

**Symptom:** After upgrading the primary Region's cluster, a secondary
Region's cluster is unavailable.

**Diagnostics:**

```bash
# 1. Check the global cluster status
aws rds describe-global-clusters \
  --global-cluster-identifier <id> \
  --query 'GlobalClusters[0].GlobalClusterMembers[*].{
    Region:Region,IsWriter:IsWriter,Cluster:DBClusterArn}'

# 2. Check the secondary cluster status in its Region
aws rds describe-db-clusters \
  --db-cluster-identifier <secondary-id> \
  --region <secondary-region> \
  --query 'DBClusters[0].{Status:Status,EngineVersion:EngineVersion}'
```

**Expected behavior:** Secondary clusters are rebuilt from the upgraded
primary. During the rebuild, the secondary is in `modifying` or
`backing-up` state and may be unavailable for reads. The rebuild can
take 2-6 hours depending on data size. No action needed — wait for
the rebuild to complete.

If the rebuild fails, the secondary enters an error state. Retry by
removing and re-adding the secondary to the global cluster (requires
deleting the secondary cluster and creating a new one from the primary).

## Diagnostic command quick-reference

| Goal | Command |
|---|---|
| Instance status | `aws rds describe-db-instances --db-instance-identifier <id>` |
| Cluster status | `aws rds describe-db-clusters --db-cluster-identifier <id>` |
| Valid upgrade targets | `aws rds describe-db-engine-versions --engine <engine> --query 'DBEngineVersions[?EngineVersion==`<current>`].ValidUpgradeTarget'` |
| Parameter groups for family | `aws rds describe-db-parameter-groups --query 'DBParameterGroups[?contains(DBParameterGroupFamily, `<family>`)]'` |
| Pending modifications | `aws rds describe-db-instances --db-instance-identifier <id> --query 'DBInstances[0].PendingModifiedValues'` |
| RDS events (failures) | `aws rds describe-events --source-type db-instance --source-identifier <id> --event-categories failure --duration 360` |
| Global cluster topology | `aws rds describe-global-clusters --global-cluster-identifier <id>` |
| Blue/green status | `aws rds describe-blue-green-deployments` |
| Snapshot status | `aws rds describe-db-snapshots --db-snapshot-id <id>` |
| Upgrade instance | `aws rds modify-db-instance --db-instance-identifier <id> --engine-version <target> --apply-immediately` |
| Upgrade cluster | `aws rds modify-db-cluster --db-cluster-identifier <id> --engine-version <target> --apply-immediately` |
| Create blue/green | `aws rds create-blue-green-deployment --source <arn> --target-engine-version <target>` |
| Switchover blue/green | `aws rds switchover-blue-green-deployment --blue-green-deployment-id <id>` |
| PITR restore | `aws rds restore-db-instance-to-point-in-time --source-db-instance-identifier <id> --target-db-instance-identifier <new> --restore-time <iso8601>` |

## Failure-mode to operation routing

| Failure mode | Recommended operation | Notes |
|---|---|---|
| Invalid target version | major-upgrade | Choose a valid target from `describe-db-engine-versions` |
| Param group gap | param-group-migrate | Create target-family param group first |
| Stuck `upgrade-failed` | rollback | PITR restore to pre-upgrade snapshot |
| MySQL 8.0 auth issue | post-upgrade-verify | Fix param group or upgrade driver |
| PostgreSQL planner regression | post-upgrade-verify | Run `ANALYZE` on all tables |
| Aurora replica lag | post-upgrade-verify | Wait for replica rebuild; monitor lag |
| Global secondary unreachable | global-upgrade | Wait for secondary rebuild; check status |
