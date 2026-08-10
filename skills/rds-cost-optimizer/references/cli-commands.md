# RDS Cost Optimizer — CLI Commands

Canonical CLI commands for live-account pre-flight data gathering. Run before
classification to avoid false positives.

## 1. Enumerate database instances and configuration

```bash
aws rds describe-db-instances --output json | jq '.DBInstances[] | {
  db_instance_id: .DBInstanceIdentifier,
  engine: .Engine,                          # "postgres", "mysql", "oracle-ee", "sqlserver-ee"
  engine_version: .EngineVersion,
  class: .DBInstanceClass,                  # "db.r6i.2xlarge"
  multi_az: .MultiAZ,                       # true | false
  storage_type: .StorageType,               # "gp3" | "io2" | "standard"
  allocated_storage: .AllocatedStorage,     # GB
  storage_throughput: .StorageThroughput,   # MB/s (gp3)
  iops: .Iops,                              # provisioned IOPS (io2, gp3 above baseline)
  license_model: .LicenseModel,             # "license-included" | "bring-your-own-license"
  publicly_accessible: .PubliclyAccessible,
  status: .DBInstanceStatus                 # "available" | "stopped" | "deleting"
}'
```

## 2. Pull 14-30 day CloudWatch utilization

```bash
START=$(date -u -d '-30 days' +%FT%TZ)
END=$(date -u +%FT%TZ)

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=<db-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum \
  --output json > cpu.json

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name FreeableMemory \
  --dimensions Name=DBInstanceIdentifier,Value=<db-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Minimum \
  --output json > mem.json

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=<db-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum \
  --output json > conns.json
```

## 3. Pull Performance Insights DBLoad and top SQL

```bash
aws pi describe-dimension-keys \
  --service-type RDS \
  --identifier <db-id> \
  --start-time $START --end-time $END \
  --metric db.load.avg \
  --group-by '{"Group":"db.sql"}' \
  --output json
```

## 4. Check existing Reserved Instances

```bash
aws rds describe-reserved-db-instances --output json | \
  jq '.ReservedDBInstances[] | {
    ri_id: .ReservedDBInstanceId,
    class: .DBInstanceClass,
    duration: .Duration,                     # 31536000 (1yr) | 94608000 (3yr)
    state: .State,                           # "active" | "retired"
    offering_type: .OfferingType             # "No Upfront" | "Partial Upfront" | "All Upfront"
  }'
```

## 5. Check Aurora Serverless v2 ACU metrics (Aurora only)

```bash
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name ACUUtilization \
  --dimensions Name=DBClusterIdentifier,Value=<cluster-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum,Minimum \
  --output json
```

## 6. Enumerate manual snapshots for cleanup candidates

```bash
aws rds describe-db-snapshots --snapshot-type manual --output json | \
  jq '.DBSnapshots[] | {
    snapshot_id: .DBSnapshotIdentifier,
    db_id: .DBInstanceIdentifier,
    created: .SnapshotCreateTime,
    size_gb: .AllocatedStorage,
    status: .Status
  }'
```

## 7. Manual snapshot cleanup

```bash
# List manual snapshots older than 90 days
aws rds describe-db-snapshots --snapshot-type manual --output json | \
  jq '.DBSnapshots[] | select(.SnapshotCreateTime < (now - 7776000))
      | {snapshot_id, db_id, created, size_gb}'

# Delete a manual snapshot
aws rds delete-db-snapshot --db-snapshot-identifier <snapshot-id>
```

## 8. Verify engine-class compatibility before recommending Graviton

```bash
aws rds describe-orderable-db-instance-options --engine postgres --db-instance-class db.r6g.large
```
