# Redshift Optimization Deep Dive

CLI scripts, WLM configuration details, storage analysis procedures, and
migration workflows referenced by the redshift-cluster-optimizer skill.

## Live-account pre-flight CLI script

```bash
#!/usr/bin/env bash
set -euo pipefail

CLUSTER_ID="${1:?Usage: $0 <cluster-identifier>}"
REGION="${2:-us-east-1}"

echo "=== Cluster metadata ==="
aws redshift describe-clusters \
  --cluster-identifier "$CLUSTER_ID" \
  --region "$REGION" \
  --query 'Clusters[0].{
    ClusterIdentifier:ClusterIdentifier,
    NodeType:NodeType,
    NumberOfNodes:NumberOfNodes,
    ClusterStatus:ClusterStatus,
    AvailabilityZone:AvailabilityZone,
    ClusterVersion:ClusterVersion,
    AllowVersionUpgrade:AllowVersionUpgrade,
    AutomatedSnapshotRetentionPeriod:AutomatedSnapshotRetentionPeriod,
    ClusterParameterGroups:ClusterParameterGroups,
    VpcSecurityGroups:VpcSecurityGroups,
    ClusterSubnetGroupName:ClusterSubnetGroupName,
    ElasticIpStatus:ElasticIpStatus,
    ClusterSnapshotCopyStatus:ClusterSnapshotCopyStatus,
    DataTransferProgress:DataTransferProgress
  }' \
  --output json

echo ""
echo "=== CloudWatch: CPUUtilization (30-day average) ==="
aws cloudwatch get-metric-statistics \
  --namespace AWS/Redshift \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterIdentifier,Value="$CLUSTER_ID" \
  --start-time "$(date -u -d '30 days ago' +%FT%TZ 2>/dev/null || date -u -v-30d +%FT%TZ)" \
  --end-time "$(date -u +%FT%TZ)" \
  --period 3600 \
  --statistics Average,Maximum,Minimum \
  --region "$REGION" \
  --output json

echo ""
echo "=== CloudWatch: QueryQueueLength (30-day average) ==="
aws cloudwatch get-metric-statistics \
  --namespace AWS/Redshift \
  --metric-name QueryQueueLength \
  --dimensions Name=ClusterIdentifier,Value="$CLUSTER_ID" \
  --start-time "$(date -u -d '30 days ago' +%FT%TZ 2>/dev/null || date -u -v-30d +%FT%TZ)" \
  --end-time "$(date -u +%FT%TZ)" \
  --period 3600 \
  --statistics Average,Maximum \
  --region "$REGION" \
  --output json

echo ""
echo "=== CloudWatch: DatabaseConnections (30-day) ==="
aws cloudwatch get-metric-statistics \
  --namespace AWS/Redshift \
  --metric-name DatabaseConnections \
  --dimensions Name=ClusterIdentifier,Value="$CLUSTER_ID" \
  --start-time "$(date -u -d '30 days ago' +%FT%TZ 2>/dev/null || date -u -v-30d +%FT%TZ)" \
  --end-time "$(date -u +%FT%TZ)" \
  --period 3600 \
  --statistics Average,Maximum \
  --region "$REGION" \
  --output json

echo ""
echo "=== CloudWatch: ConcurrencyScalingClustersActive (30-day) ==="
aws cloudwatch get-metric-statistics \
  --namespace AWS/Redshift \
  --metric-name ConcurrencyScalingClustersActive \
  --dimensions Name=ClusterIdentifier,Value="$CLUSTER_ID" \
  --start-time "$(date -u -d '30 days ago' +%FT%TZ 2>/dev/null || date -u -v-30d +%FT%TZ)" \
  --end-time "$(date -u +%FT%TZ)" \
  --period 3600 \
  --statistics Average,Maximum,Sum \
  --region "$REGION" \
  --output json

echo ""
echo "=== Reserved Nodes ==="
aws redshift describe-reserved-nodes \
  --region "$REGION" \
  --output json

echo ""
echo "=== Cost Explorer: Redshift spend (30-day) ==="
aws ce get-cost-and-usage \
  --time-period Start="$(date -u -d '30 days ago' +%F 2>/dev/null || date -u -v-30d +%F)",End="$(date -u +%F)" \
  --granularity MONTHLY \
  --filter '{"Service":"Redshift"}' \
  --metrics "BlendedCost" "UsageQuantity" \
  --region "$REGION" \
  --output json
```

## Serverless pre-flight

```bash
WORKGROUP="${1:?Usage: $0 <workgroup-name>}"
REGION="${2:-us-east-1}"

echo "=== Serverless workgroup metadata ==="
aws redshift-serverless get-workgroup \
  --workgroup-name "$WORKGROUP" \
  --region "$REGION" \
  --output json

echo ""
echo "=== Serverless RPU usage (30-day) ==="
aws cloudwatch get-metric-statistics \
  --namespace AWS/RedshiftServerless \
  --metric-name RPUSeconds \
  --dimensions Name=WorkgroupName,Value="$WORKGROUP" \
  --start-time "$(date -u -d '30 days ago' +%FT%TZ 2>/dev/null || date -u -v-30d +%FT%TZ)" \
  --end-time "$(date -u +%FT%TZ)" \
  --period 3600 \
  --statistics Sum \
  --region "$REGION" \
  --output json
```

## Storage analysis queries

Connect to the Redshift cluster and run these to evaluate storage health.

### Column compression audit

```sql
-- Identify uncompressed columns (ENCODE = none)
SELECT
  schemaname,
  tablename,
  "column",
  encode,
  type,
  encoding
FROM pg_table_def
WHERE encode = 'none'
ORDER BY schemaname, tablename;
```

### Table bloat (unvacuumed soft-deleted rows)

```sql
-- Estimate space reclaimable via VACUUM
SELECT
  ti."schema" AS schemaname,
  ti."table" AS tablename,
  ti."table" AS tbl,
  stv_tbl_perm.name AS table_name,
  COUNT(*) AS mb_used
FROM stv_tbl_perm
JOIN svv_table_info ti
  ON ti."table" = stv_tbl_perm.name
GROUP BY 1, 2, 3, 4
ORDER BY mb_used DESC;
```

### Stale ANALYZE statistics

```sql
-- Tables with outdated planner statistics
SELECT
  schemaname,
  tablename,
  last_analyze,
  last_auto_analyze,
  has_stats
FROM svv_table_info
ORDER BY last_analyze NULLS FIRST;
```

## WLM configuration reference

### Auto WLM with SQA (recommended default)

```sql
-- Enable Auto WLM with Short Query Acceleration
SET wlm_json_configuration = '[
  {
    "auto_wlm": true,
    "short_query_queue_enable": true,
    "query_concurrency": 10
  }
]';
```

### Manual WLM with multiple queues

```sql
-- Queue 1: Short interactive BI (high priority)
-- Queue 2: Long ETL (lower priority, higher concurrency)
SET wlm_json_configuration = '[
  {
    "name": "BI-queries",
    "query_concurrency": 5,
    "priority": "High",
    "max_execution_time": 300000,
    "user_group": ["bi_users"],
    "query_group": ["bi_reports"]
  },
  {
    "name": "ETL-queries",
    "query_concurrency": 15,
    "priority": "Low",
    "max_execution_time": 7200000,
    "user_group": ["etl_users"],
    "query_group": ["etl_loads"],
    "concurrency_scaling": "auto"
  }
]';
```

## DC2 to RA3 migration procedure

### Step 1: Snapshot the source cluster

```bash
aws redshift create-snapshot \
  --cluster-identifier source-dc2-cluster \
  --snapshot-identifier dc2-to-ra3-migration-$(date +%s) \
  --region us-east-1
```

### Step 2: Restore as RA3 (or elastic resize)

Option A: Restore from snapshot (longer, but safer for large clusters):

```bash
aws redshift restore-from-cluster-snapshot \
  --cluster-identifier new-ra3-cluster \
  --snapshot-identifier dc2-to-ra3-migration-<timestamp> \
  --node-type ra3.4xlarge \
  --number-of-nodes <desired_count> \
  --region us-east-1
```

Option B: Elastic resize (faster, in-place, but limited to compatible types):

```bash
aws redshift resize-cluster \
  --cluster-identifier source-dc2-cluster \
  --cluster-type multi-node \
  --node-type ra3.4xlarge \
  --number-of-nodes <desired_count> \
  --region us-east-1
```

### Step 3: Verify data integrity

```sql
-- Compare row counts between source and target
SELECT 'orders' AS tbl, COUNT(*) FROM orders
UNION ALL
SELECT 'lineitems', COUNT(*) FROM lineitems
UNION ALL
SELECT 'customers', COUNT(*) FROM customers;
```

### Step 4: Update application connection strings

Update JDBC/ODBC endpoints to point to the new RA3 cluster endpoint.

### Step 5: Decommission the old DC2 cluster

```bash
aws redshift delete-cluster \
  --cluster-identifier source-dc2-cluster \
  --final-cluster-snapshot-identifier final-dc2-snapshot \
  --region us-east-1
```

## Concurrency Scaling cost analysis

```bash
# Check how many hours Concurrency Scaling clusters were active in the last 30 days
aws cloudwatch get-metric-statistics \
  --namespace AWS/Redshift \
  --metric-name ConcurrencyScalingClustersActive \
  --dimensions Name=ClusterIdentifier,Value="$CLUSTER_ID" \
  --start-time "$(date -u -d '30 days ago' +%FT%TZ 2>/dev/null || date -u -v-30d +%FT%TZ)" \
  --end-time "$(date -u +%FT%TZ)" \
  --period 86400 \
  --statistics Sum \
  --region us-east-1 \
  --output json

# Monthly CS cost estimate: Sum datapoints x $1.08
# Compare with Reserved Node cost for the equivalent capacity.
```

## Data sharing setup

```sql
-- On the producer cluster:
CREATE DATASHARE sales_datashare;
ALTER DATASHARE sales_datashare ADD SCHEMA PUBLIC;
ALTER DATASHARE sales_datashare ADD TABLE sales_data;
ALTER DATASHARE sales_datashare ADD VIEW daily_sales_summary;

-- Grant access to a consumer namespace:
GRANT USAGE ON DATASHARE sales_datashare TO NAMESPACE 'consumer-cluster-namespace-uuid';
```

```sql
-- On the consumer cluster:
CREATE EXTERNAL SCHEMA sales_ext
FROM DATASHARE sales_datashare
WITH (PROVIDER NAMESPACE 'producer-cluster-namespace-uuid');

-- Query the shared data directly:
SELECT * FROM sales_ext.daily_sales_summary LIMIT 10;
```

## Materialized view creation

```sql
-- Create a materialized view for a frequently queried aggregation
CREATE MATERIALIZED VIEW daily_revenue_mv
AUTO REFRESH YES
AS
SELECT
  date_trunc('day', order_date) AS day,
  region,
  SUM(amount) AS total_revenue,
  COUNT(*) AS order_count
FROM orders
GROUP BY 1, 2;

-- For large datasets, use incremental refresh:
ALTER MATERIALIZED VIEW daily_revenue_mv
SET ENABLE AUTO REFRESH;
```
