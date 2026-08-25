# Diagnostic commands — rds-failover-troubleshooter (load on demand)

Moved verbatim from SKILL.md; load only when needed.

## Account-wide pre-flight commands

```bash
# 1. Cluster configuration (Aurora)
aws rds describe-db-clusters \
  --db-cluster-identifier <cluster-id> --output json | \
  jq '.DBClusters[] | {DBClusterIdentifier, Engine, EngineVersion, Status,
    MultiAZ, DBClusterMembers, Endpoint, ReaderEndpoint,
    DBClusterParameterGroup, AllocatedStorage, StorageEncrypted}'

# 2. Instance details (primary and replicas)
aws rds describe-db-instances \
  --db-instance-identifier <instance-id> --output json | \
  jq '.DBInstances[] | {DBInstanceIdentifier, DBInstanceClass, DBInstanceStatus,
    MultiAZ, PromotionTier, DBParameterGroups, OptionGroupMemberships,
    AllocatedStorage, StorageType, Engine, Endpoint}'

# 3. Cluster endpoints (Aurora)
aws rds describe-db-cluster-endpoints \
  --db-cluster-identifier <cluster-id> --output json

# 4. Recent RDS events
aws rds describe-events \
  --source-identifier <cluster-id> --source-type db-cluster \
  --start-time $(date -d '-2 hours' +%FT%TZ) --output json

# 5. CloudWatch failover-related metrics
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBClusterIdentifier,Value=<cluster-id> \
  --start-time $(date -d '-2 hours' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum,Average --output json

# 6. Free storage space
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=<instance-id> \
  --start-time $(date -d '-2 hours' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Minimum --output json
```

## Step 1 — Application connection string check (probe)

```bash
# Check what endpoint the application is using
# Look for the connection string in the application configuration
grep -r "rds.amazonaws.com" /path/to/app/config/

# Verify the cluster endpoint resolves to the new writer
dig +short <cluster-endpoint>

# Compare with the instance endpoint
dig +short <instance-endpoint>
```

## Step 2 — DNS propagation check (probe)

```bash
# Check DNS TTL for the Aurora cluster endpoint
dig <cluster-endpoint> | grep "ANSWER SECTION" -A 5

# Aurora cluster endpoints have a 1-second TTL by default
# If the application's DNS resolver ignores the TTL, the old IP persists
```

## Step 3 — Multi-AZ health check threshold (probe)

```bash
aws rds describe-db-instances \
  --db-instance-identifier <instance-id> --output json | \
  jq '.DBInstances[] | {MultiAZ, DBInstanceStatus, AutomatedBackupRetentionPeriod}'

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=<instance-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

## Step 4 — Failover priority tier (probe)

```bash
aws rds describe-db-clusters \
  --db-cluster-identifier <cluster-id> --output json | \
  jq '.DBClusters[].DBClusterMembers[] | {DBInstanceIdentifier,
    IsClusterWriter, PromotionTier}'

# Check each instance's tier
aws rds describe-db-instances --output json | \
  jq '.DBInstances[] | select(.DBClusterIdentifier == "<cluster-id>") |
    {DBInstanceIdentifier, DBInstanceClass, PromotionTier}'
```

## Step 4 — Failover priority tier (fix)

```bash
aws rds modify-db-instance \
  --db-instance-identifier <target-instance> \
  --promotion-tier 0 --apply-immediately
```

## Step 5 — Storage-full check (probe)

```bash
aws rds describe-db-instances \
  --db-instance-identifier <instance-id> --output json | \
  jq '.DBInstances[] | {DBInstanceStatus, AllocatedStorage, StorageType}'

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=<instance-id> \
  --start-time $(date -d '-2 hours' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Minimum --output json
```

## Step 5 — Storage-full check (fix)

```bash
aws rds modify-db-instance \
  --db-instance-identifier <instance-id> \
  --allocated-storage <new-size> --apply-immediately
```

## Step 6 — Parameter group mismatch (probe)

```bash
# Compare parameter groups on primary and standby
aws rds describe-db-instances --output json | \
  jq '.DBInstances[] | select(.DBClusterIdentifier == "<cluster-id>") |
    {DBInstanceIdentifier, DBParameterGroups, OptionGroupMemberships}'

# Check for pending parameter changes
aws rds describe-db-instances \
  --db-instance-identifier <instance-id> --output json | \
  jq '.DBInstances[].DBParameterGroups[] | {DBParameterGroupName,
    ParameterApplyStatus}'
```

## Step 6 — Parameter group mismatch (fix)

```bash
aws rds modify-db-instance \
  --db-instance-identifier <standby-id> \
  --db-parameter-group-name <primary-param-group> \
  --apply-immediately
```

## Step 7 — Option group conflict (probe)

```bash
# Compare option groups
aws rds describe-db-instances --output json | \
  jq '.DBInstances[] | select(.DBClusterIdentifier == "<cluster-id>") |
    {DBInstanceIdentifier, OptionGroupMemberships}'

# Check for pending option group changes
aws rds describe-db-instances \
  --db-instance-identifier <instance-id> --output json | \
  jq '.DBInstances[].OptionGroupMemberships[] | {OptionGroupName,
    Status}'
```

## Step 7 — Option group conflict (fix)

```bash
aws rds modify-db-instance \
  --db-instance-identifier <standby-id> \
  --option-group-name <primary-option-group> \
  --apply-immediately
```

## Step 8 — Read replica promotion failure (probe)

```bash
aws rds describe-db-instances \
  --db-instance-identifier <replica-id> --output json | \
  jq '.DBInstances[] | {DBInstanceStatus, ReadReplicaSourceDBInstanceIdentifier,
    DBInstanceClass, AllocatedStorage}'

# Check replication lag
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name AuroraReplicaLag \
  --dimensions Name=DBInstanceIdentifier,Value=<replica-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Maximum --output json
```

## Step 9 — Aurora Global DB failover mode (probe)

```bash
aws rds describe-global-clusters \
  --global-cluster-identifier <global-cluster-id> --output json | \
  jq '.GlobalClusters[] | {GlobalClusterIdentifier, GlobalClusterMembers,
    FailoverConfig}'

# Check the failover mode
aws rds describe-global-clusters --output json | \
  jq '.GlobalClusters[] | .FailoverConfig'
```

## Step 10 — RDS Proxy failover (probe)

```bash
aws rds describe-db-proxies \
  --db-proxy-name <proxy-name> --output json | \
  jq '.DBProxies[] | {DBProxyName, Status, EngineFamily,
    TargetRole, RequireTLS}'

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBProxyIdentifier,Value=<proxy-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average --output json
```

## Step 11 — Recovery mode (Aurora probe)

```bash
aws rds describe-db-clusters \
  --db-cluster-identifier <cluster-id> --output json | \
  jq '.DBClusters[] | {EngineVersion, DBClusterParameterGroup}'
```

## Step 11 — Recovery mode (Multi-AZ probe)

```bash
aws rds describe-db-parameters \
  --db-parameter-group-name <param-group> --output json | \
  jq '.Parameters[] | select(.ParameterName == "recovery_mode")'
```

## Step 12 — CloudWatch failover event gap (probe)

```bash
# Check RDS events
aws rds describe-events \
  --source-identifier <cluster-id> --source-type db-cluster \
  --start-time $(date -d '-2 hours' +%FT%TZ) --output json

# Check EventBridge rules for RDS
aws events list-rules --output json | \
  jq '.Rules[] | select(.EventPattern | contains("rds"))'
```

