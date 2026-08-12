# End-to-end usage scenario: rds-upgrade-operator

A walkthrough showing the skill planning a blue/green major upgrade
(Aurora MySQL 5.7 to 8.0) with the driver-compatibility review surfaced
by the pre-check gate, followed by the contrast case where a missing
parameter group blocks the upgrade.

## Input (user prompt)

> We need to upgrade `prod-payments-cluster` from Aurora MySQL 5.7 to
> 8.0. We want to use blue/green for zero downtime. The target
> parameter and option groups are ready. The application uses MySQL
> Connector/J 5.1.49. Schedule the switchover for Sunday 03:00 UTC.

```json
{
  "Operation": "blue-green-upgrade",
  "Cluster": "prod-payments-cluster",
  "TargetEngineVersion": "8.0.mysql_aurora.3.04.0",
  "ClusterMetadata": {
    "Status": "available",
    "Engine": "aurora-mysql",
    "EngineVersion": "5.7.mysql_aurora.2.11.4",
    "DBClusterParameterGroup": "aurora-mysql5.7-payments-custom"
  },
  "TargetParameterGroup": "aurora-mysql8.0-payments-custom",
  "TargetOptionGroup": "aurora-mysql8.0-payments-opts (MEMCACHED removed)",
  "PreUpgradeSnapshot": "prod-payments-pre-8-0 (available)",
  "ApplicationDriver": "MySQL Connector/J 5.1.49",
  "SwitchoverWindow": "Sunday 03:00 UTC"
}
```

## Skill output

```text
OPERATION: blue-green-upgrade
VERDICT: REVIEW_REQUIRED
TARGET: prod-payments-cluster (engine: aurora-mysql 5.7.mysql_aurora.2.11.4 -> 8.0.mysql_aurora.3.04.0)
PRE_CHECKS:
  - [PASS] DBClusterStatus: available
  - [PASS] describe-db-engine-versions confirms 8.0 target is valid
  - [PASS] Target parameter group aurora-mysql8.0-payments-custom
    exists (12 custom params diffed and reproduced)
  - [PASS] Target option group aurora-mysql8.0-payments-opts exists
    (MEMCACHED removed — not supported in Aurora MySQL 8.0)
  - [PASS] Pre-upgrade snapshot prod-payments-pre-8-0 available
  - [REVIEW] Application driver: MySQL Connector/J 5.1.49 — does NOT
    support caching_sha2_password (the default auth plugin in MySQL 8.0).
    Options: (a) upgrade driver to 8.0.x, OR (b) set
    default_authentication_plugin=mysql_native_password in the target
    parameter group. Review and confirm the approach.
  - [REVIEW] Blue/green provisioning window: 45-90 minutes. The green
    cluster will be provisioned and kept in sync via logical replication.
    Switchover scheduled for Sunday 03:00 UTC. Confirm the window.
  - [REVIEW] Rollback plan: after switchover, the blue (old 5.7)
    environment is retained for 72 hours as a rollback safety net.
    Confirm the blue deletion schedule (Wednesday 03:00 UTC).
STEPS:
  1. CONFIRM: About to create a blue/green deployment for
     prod-payments-cluster, upgrading Aurora MySQL 5.7 to 8.0. The
     green environment will be provisioned over 45-90 minutes, then
     held for a scheduled switchover at Sunday 03:00 UTC. Proceed?
     (yes/no)
  2. aws rds create-blue-green-deployment \
       --blue-green-deployment-name prod-payments-bg-8-0 \
       --source arn:aws:rds:us-east-1:111111111111:cluster:prod-payments-cluster \
       --target-engine-version 8.0.mysql_aurora.3.04.0 \
       --delete-automated-backups false
  3. aws rds wait blue-green-deployment-provisioning-complete \
       --blue-green-deployment-id <bg-id>
  4. (Scheduled switchover at Sunday 03:00 UTC)
     aws rds switchover-blue-green-deployment \
       --blue-green-deployment-id <bg-id>
  5. aws rds wait blue-green-deployment-switchover-complete \
       --blue-green-deployment-id <bg-id>
POST_VERIFY:
  - (pending switchover)
  - [PASS] EngineVersion: 8.0.mysql_aurora.3.04.0
  - [PASS] All cluster members report 8.0
  - [PASS] Application connectivity with Connector/J 8.0.x: OK
  - [PASS] Performance Insights: AAS and top-query latency within
    +/- 15% of baseline
NOTES:
  - Blue/green switchover is under 60 seconds (DNS shift). The green
    (8.0) becomes the new production; the blue (5.7) is retained for
    72 hours as rollback.
  - Rollback: switchover back to blue within 72 hours. After 72 hours,
    rollback requires PITR restore.
  - MEMCACHED option removed (not supported in Aurora MySQL 8.0).
  - Run ANALYZE on the green after provisioning to refresh PostgreSQL-
    style statistics (MySQL uses ANALYZE TABLE; the green's stats are
    copied from the blue at provisioning time).
```

## Contrast — REVIEW_REQUIRED case (missing parameter group)

If the operator had not pre-created a parameter group for the
`aurora-mysql8.0` family, the pre-check gate would surface the gap:

```text
OPERATION: major-upgrade
VERDICT: REVIEW_REQUIRED
TARGET: prod-analytics-cluster (engine: aurora-postgresql 13.8 -> 14.9)
PRE_CHECKS:
  - [PASS] DBClusterStatus: available
  - [PASS] describe-db-engine-versions confirms 14.9 is valid
  - [REVIEW] No custom aurora-postgresql14 parameter group found. The
    source group aurora-postgresql13-analytics-custom has 15 custom
    parameters (shared_preload_libraries, max_connections, work_mem,
    etc.) that CANNOT be applied via the default.aurora-postgresql14
    group. Create a custom aurora-postgresql14 parameter group, diff
    and apply the 15 custom parameters, then re-plan the upgrade.
STEPS: (none — parameter group gap must be resolved first)
POST_VERIFY: (none)
NOTES:
  - Create the target parameter group:
    aws rds create-db-cluster-parameter-group \
      --db-cluster-parameter-group-name aurora-postgresql14-analytics-custom \
      --db-parameter-group-family aurora-postgresql14 \
      --description "Custom params for Aurora PostgreSQL 14 analytics"
  - Diff and apply the 15 custom parameters from the 13-family group.
  - Re-plan the upgrade after the parameter group is ready.
```

## What the skill caught that a generic assistant misses

1. **Driver compatibility flag.** A generic assistant emits the
   `create-blue-green-deployment` command without checking the
   application driver. The skill surfaces that Connector/J 5.1.49 does
   NOT support `caching_sha2_password` — the default in MySQL 8.0.
   Without this check, the switchover would succeed but all
   application authentication would fail.

2. **Parameter group family compatibility.** A generic assistant
   assumes the existing parameter group carries over. The skill knows
   that `aurora-mysql5.7` param groups are NOT compatible with 8.0 —
   the upgrade would fail or silently drop custom parameters.

3. **MEMCACHED removal.** A generic assistant omits this. The skill
   flags that MEMCACHED was removed in Aurora MySQL 8.0 so the
   operator can confirm no application dependency.

4. **Blue/green rollback window.** A generic assistant omits the
   rollback plan. The skill specifies the 72-hour retention of the
   blue environment and the Wednesday deletion schedule.

5. **Post-upgrade ANALYZE.** A generic assistant says "verify after
   switchover." The skill names the specific verification steps:
   EngineVersion check, all cluster members check, Performance Insights
   comparison, and driver connectivity test.

6. **Explicit opt-in for major versions.** A generic assistant omits
   that `AutoMinorVersionUpgrade` only handles minor patches. The skill
   confirms this is an explicit major version upgrade requiring
   operator sign-off.

## Slash-command invocation

```
/aws:operate-rds-upgrade
```

Or via the orchestrator:

```
/aws:pipeline
You: "upgrade prod-payments-cluster to Aurora MySQL 8.0"
```

The orchestrator emits
`[Phase: Operate | Skills routed: rds-upgrade-operator]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "upgrade prod-payments-cluster to Aurora MySQL 8.0"
# [Phase: Operate | Skills routed: rds-upgrade-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the blue/green switchover completes:

```bash
# Verify the new EngineVersion
aws rds describe-db-clusters \
  --db-cluster-identifier prod-payments-cluster \
  --profile default \
  --query 'DBClusters[0].{Engine:Engine,Version:EngineVersion,Status:Status}'

# Verify all cluster members are on 8.0
aws rds describe-db-clusters \
  --db-cluster-identifier prod-payments-cluster \
  --profile default \
  --query 'DBClusters[0].DBClusterMembers[*].DBInstanceIdentifier'

for instance in $(aws rds describe-db-clusters \
  --db-cluster-identifier prod-payments-cluster \
  --query 'DBClusters[0].DBClusterMembers[*].DBInstanceIdentifier' \
  --output text --profile default); do
  aws rds describe-db-instances \
    --db-instance-identifier $instance \
    --query 'DBInstances[0].{Instance:DBInstanceIdentifier,Version:EngineVersion}' \
    --profile default
done

# Verify application connectivity
mysql -h <cluster-endpoint> -P 3306 -u <user> -p -e "SELECT VERSION();"

# Set up a CloudWatch alarm for failover
aws cloudwatch put-metric-alarm \
  --alarm-name payments-cluster-failover \
  --namespace AWS/RDS \
  --metric-name AWSCloudWatchFailoverComplete \
  --dimensions Name=DBClusterIdentifier,Value=prod-payments-cluster \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --period 60 --evaluation-periods 1 \
  --profile default
```
