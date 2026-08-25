# Green Validation and Database Changes — RDS Blue/Green Deployer

Deep reference on green environment validation (engine version
verification, replication lag, schema correctness, query performance,
application testing), database changes in green (major version upgrade,
parameter group changes, schema changes / DDL), the blue-frozen
requirement, and monitoring during validation. Loaded on demand by the
skill — kept out of the main SKILL.md body so the deployment procedure
stays scannable.

## Green environment validation

### Why validation matters

Green validation is the LAST checkpoint before switchover. Once you
switch over, green becomes production. Any issue in green becomes a
production issue. Validation is your opportunity to catch problems
while blue is still serving traffic and rollback is trivial (just do
not switch over).

### Validation checklist

| Check | What to verify | How to verify | Pass criteria |
|---|---|---|---|
| Engine version | Green runs target version | `describe-db-instances` on green | Version matches target |
| Instance class | Green has correct instance class | `describe-db-instances` on green | Class matches or exceeds blue |
| Storage | Green has sufficient storage | Check `AllocatedStorage` and `FreeStorageSpace` | Free > 20% |
| Replication lag | Blue-to-green lag is near-zero | Check Blue/Green status or CloudWatch | < 1 second |
| Schema correctness | DDL changes applied to green | Query green information_schema | Expected columns/indexes exist |
| Data freshness | Green data matches blue | Compare row counts or checksums | Within replication lag tolerance |
| Query performance | No regression vs blue | Run EXPLAIN on critical queries | Similar or better execution plans |
| Parameter changes | Parameters applied to green | `describe-db-parameters` on green | Values match target |
| Application tests | App works against green | Point staging app at green endpoint | All tests pass |
| Connections | Green accepts connections | Test connect from app subnet | Successful connection |

### Verifying engine version on green

```bash
aws rds describe-db-instances \
  --db-instance-identifier "green-prod-mysql-db" \
  --query 'DBInstances[0].{Engine:Engine,EngineVersion:EngineVersion,Status:DBInstanceStatus}' \
  --region us-east-1 --output table
```

For Aurora clusters, check the cluster:

```bash
aws rds describe-db-clusters \
  --db-cluster-identifier "green-prod-mysql-cluster" \
  --query 'DBClusters[0].{Engine:Engine,EngineVersion:EngineVersion,Status:Status}' \
  --region us-east-1 --output table
```

### Checking replication lag

```bash
# Check Blue/Green deployment status (AVAILABLE means green is in sync)
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier "bg-prod-upgrade-2026" \
  --query 'BlueGreenDeployments[0].{Status:Status,Source:Source,Target:Target}' \
  --region us-east-1 --output table

# For Aurora MySQL, check replica lag via CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name AuroraReplicaLag \
  --dimensions Name=DBClusterIdentifier,Value=green-prod-mysql-cluster \
  --start-time $(date -u -v-5M +"%Y-%m-%dT%H:%M:%S") \
  --end-time $(date -u +"%Y-%m-%dT%H:%M:%S") \
  --period 60 \
  --statistics Average \
  --region us-east-1
```

### Schema verification on green

```bash
# MySQL: verify a column was added in green
mysql -h green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com \
  -u admin -p \
  -e "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns
      WHERE table_schema='mydb' AND table_name='orders'
      ORDER BY ORDINAL_POSITION;"

# PostgreSQL: verify a column and check indexes
psql -h green-prod-pg-db.xxx.us-east-1.rds.amazonaws.com \
  -U admin -d mydb \
  -c "\d orders"
```

### Query performance comparison

Run the same EXPLAIN on both blue and green for critical queries:

```bash
# Blue (current production)
mysql -h prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com \
  -u admin -p mydb \
  -e "EXPLAIN SELECT * FROM orders WHERE customer_id = 12345 ORDER BY created_at DESC LIMIT 10;"

# Green (staging with changes)
mysql -h green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com \
  -u admin -p mydb \
  -e "EXPLAIN SELECT * FROM orders WHERE customer_id = 12345 ORDER BY created_at DESC LIMIT 10;"
```

Compare execution plans. A major version upgrade (e.g., MySQL 5.7 →
8.0) can change the query optimizer behavior. Look for:
- Different index usage.
- Different join strategies.
- Full table scans that did not occur on blue.

## Database changes in green

### Major version upgrade in green

The major version upgrade is specified at Blue/Green creation time
via `--target-engine-version`. The upgrade happens during green
provisioning. After green is `AVAILABLE`, it runs the target version.

```bash
# Create Blue/Green with major version upgrade target
aws rds create-blue-green-deployment \
  --blue-green-deployment-name "bg-prod-upgrade-2026" \
  --source arn:aws:rds:us-east-1:123456789012:db:prod-mysql-db \
  --target-engine-version "8.0" \
  --target-db-parameter-group-name "prod-mysql80-params" \
  --region us-east-1
```

**Supported major version upgrade paths:**

| Engine | Supported paths |
|---|---|
| Aurora MySQL | 5.7 → 8.0 |
| Aurora PostgreSQL | 12 → 13, 13 → 14, 14 → 15, 15 → 16 |
| RDS MySQL | 5.7 → 8.0 |
| RDS PostgreSQL | 12 → 13, 13 → 14, 14 → 15, 15 → 16 |

**Unsupported paths:** skipping two major versions (e.g., PostgreSQL
12 → 15 directly). For these, run two sequential Blue/Green Deployments
(12 → 13, then 13 → 15).

### Parameter group changes in green

Apply a new parameter group to green at creation time or after
creation:

```bash
# At creation
aws rds create-blue-green-deployment \
  --source arn:aws:rds:us-east-1:123456789012:db:prod-pg-db \
  --target-db-parameter-group-name "prod-pg14-tuned" \
  --region us-east-1

# After creation (modify green only)
aws rds modify-db-instance \
  --db-instance-identifier "green-prod-pg-db" \
  --db-parameter-group-name "prod-pg14-tuned" \
  --apply-immediately \
  --region us-east-1
```

**Static vs dynamic parameters:**
- Dynamic parameters: applied immediately without reboot.
- Static parameters: require a DB instance reboot to take effect.

```bash
# Reboot green to apply static parameters (green only — never blue)
aws rds reboot-db-instance \
  --db-instance-identifier "green-prod-pg-db" \
  --region us-east-1
```

### Schema changes (DDL) in green

Schema changes are executed by connecting to the GREEN endpoint and
running DDL. These changes do NOT affect blue.

**Critical rules for DDL in green:**
1. Connect ONLY to the green endpoint — never blue.
2. Run DDL during low-traffic periods (DDL can lock tables).
3. Verify DDL success before switchover.
4. Do NOT run DDL on blue — it breaks logical replication.

```bash
# Connect to GREEN and add a column
mysql -h green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com \
  -u admin -p mydb \
  -e "ALTER TABLE orders ADD COLUMN status_code INT DEFAULT 0;"

# Connect to GREEN and create an index
mysql -h green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com \
  -u admin -p mydb \
  -e "CREATE INDEX idx_orders_status_code ON orders(status_code);"

# PostgreSQL: add a column with default
psql -h green-prod-pg-db.xxx.us-east-1.rds.amazonaws.com \
  -U admin -d mydb \
  -c "ALTER TABLE orders ADD COLUMN status_code INTEGER DEFAULT 0;"
```

### The blue-frozen requirement

During the entire Blue/Green lifecycle (from creation to switchover),
blue is FROZEN. This means:

| Action on blue | Allowed? | Impact |
|---|---|---|
| Application read/write traffic | YES — normal operation | Replicated to green |
| Parameter group change | NO | Breaks replication |
| Option group change | NO | Breaks replication |
| DDL (ALTER TABLE, CREATE INDEX) | NO | Breaks logical replication |
| Major version upgrade | NO | Use Blue/Green for this |
| Minor version upgrade | NO | Wait until after switchover |
| Instance class change | NO | Do after switchover |

**Why DDL on blue breaks replication:** logical replication captures
data changes (INSERT/UPDATE/DELETE), not schema changes. If you change
the schema on blue (e.g., add a column), green does not know about
the new column. When blue replicates an INSERT that includes the new
column, green fails to apply it because the column does not exist.

## Monitoring during green validation

### CloudWatch metrics to watch

```bash
# Green DB CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=green-prod-mysql-db \
  --start-time $(date -u -v-15M +"%Y-%m-%dT%H:%M:%S") \
  --end-time $(date -u +"%Y-%m-%dT%H:%M:%S") \
  --period 300 \
  --statistics Average,Maximum \
  --region us-east-1

# Green DB free storage
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name FreeStorageSpace \
  --dimensions Name=DBInstanceIdentifier,Value=green-prod-mysql-db \
  --start-time $(date -u -v-15M +"%Y-%m-%dT%H:%M:%S") \
  --end-time $(date -u +"%Y-%m-%dT%H:%M:%S") \
  --period 300 \
  --statistics Average \
  --region us-east-1

# Green DB database connections
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=green-prod-mysql-db \
  --start-time $(date -u -v-15M +"%Y-%m-%dT%H:%M:%S") \
  --end-time $(date -u +"%Y-%m-%dT%H:%M:%S") \
  --period 300 \
  --statistics Average \
  --region us-east-1
```

### Enhanced Monitoring

If Enhanced Monitoring is enabled, you get OS-level metrics (CPU,
memory, disk I/O) for green:

```bash
# List Enhanced Monitoring logs for green
aws logs describe-log-streams \
  --log-group-name RDSOSMetrics \
  --log-stream-name-prefix green-prod-mysql-db \
  --max-items 5 \
  --region us-east-1
```

## Common validation pitfalls

### Pitfall 1: Not testing application compatibility

A major version upgrade can change SQL behavior (e.g., reserved
words, default authentication plugins). Testing only schema and data
is not enough — the application must be tested against green.

**Fix:** deploy a staging instance of the application pointing at the
green endpoint. Run the full test suite. Check for SQL compatibility
errors.

### Pitfall 2: Extension compatibility (PostgreSQL)

PostgreSQL major version upgrades may require extension upgrades.
Extensions that worked on PostgreSQL 13 may need updates for
PostgreSQL 15.

**Fix:** after green provisioning, check extension status:

```bash
psql -h green-prod-pg-db.xxx.us-east-1.rds.amazonaws.com \
  -U admin -d mydb \
  -c "SELECT extname, extversion FROM pg_extension ORDER BY extname;"
```

Upgrade extensions if needed:

```bash
psql -h green-prod-pg-db.xxx.us-east-1.rds.amazonaws.com \
  -U admin -d mydb \
  -c "ALTER EXTENSION postgis UPDATE TO '3.4.2';"
```

### Pitfall 3: Character set and collation changes

Major version upgrades can change default character sets or
collations. This affects string comparisons and sorting.

**Fix:** verify character set and collation on green match
expectations. Run representative ORDER BY queries on green and
compare results with blue.

### Pitfall 4: Not checking replication lag before switchover

High replication lag means green is stale. Switching over with high
lag increases downtime (the switchover must drain lag first).

**Fix:** always check the Blue/Green status is `AVAILABLE` (not
`UPGRADING` or `PROVISIONING`) and replication lag is near-zero
before initiating switchover.

---

### Parameter group changes in green (moved from SKILL.md)

Apply a different parameter group to green (specified at creation via
`--target-db-parameter-group-name`). To change parameters in green
after creation:

```bash
# Modify green's parameter group (green DB only)
aws rds modify-db-instance \
  --db-instance-identifier "green-prod-mysql-db" \
  --db-parameter-group-name "prod-mysql80-tuned-params" \
  --apply-immediately \
  --region us-east-1
```

### Schema changes (DDL) in green (moved from SKILL.md)

Schema changes (ALTER TABLE, CREATE INDEX, etc.) are executed in
green ONLY. These changes do NOT affect blue and are replicated to
green via the logical replication stream from blue.

```bash
# Connect to green and run DDL (example: add a column)
# Use the green endpoint — NEVER the blue endpoint
mysql -h green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com \
  -u admin -p \
  -e "ALTER TABLE orders ADD COLUMN status_code INT DEFAULT 0;"
```

**Critical:** Run DDL ONLY against the green endpoint. Running DDL
against blue during the Blue/Green lifecycle breaks logical
replication and can corrupt the switchover.

