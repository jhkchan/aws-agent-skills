# Redshift WLM Configuration and Pricing Reference

Supplementary reference for the Redshift WLM Optimizer skill. Loaded on-demand
when detailed WLM JSON schemas, pricing tables, SQA threshold guidance, QMR
metric references, or AQUA acceleration patterns are needed.

## Redshift pricing (us-east-1, 2026, USD)

### RA3 node pricing (managed storage)

| Node type | vCPU | RAM (GB) | Managed storage | $/node-hour |
|---|---|---|---|---|
| ra3.large | 2 | 16 | 8 TB | $0.250 |
| ra3.4xlarge | 12 | 96 | 128 TB | $3.024 |
| ra3.16xlarge | 48 | 384 | 128 TB | $12.096 |

### Concurrency scaling pricing

- Billed per second of active cluster time (60-second minimum).
- Same $/node-hour rate as the primary cluster's node type.
- Typical cost: sub-5% of primary cluster monthly cost for bursty workloads.
- Cost visibility: AWS Cost Explorer, usage type
  `Redshift:ConcurrencyScaling`.

### Serverless pricing (different surface)

- RPU-hours (Redshift Processing Units): $0.36/RPU-hour.
- Base capacity: 8 RPUs minimum; scales in RPU increments.
- This skill does NOT optimize Serverless clusters — different config.

### Free tier

- 750 hours/month of `ra3.large` single-node for the first 2 months.
- Concurrency scaling is NOT included in the free tier.

## WLM JSON schema

### Auto WLM configuration (recommended)

```json
[
  {
    "queue_name": "priority-queries",
    "auto_wlm": true,
    "concurrency_scaling": "auto",
    "priority": "highest",
    "user_group": ["dashboard_users"],
    "query_group": []
  },
  {
    "queue_name": "etl",
    "auto_wlm": true,
    "concurrency_scaling": "auto",
    "priority": "normal",
    "query_group": ["batch_etl"]
  },
  {
    "queue_name": "ad-hoc",
    "auto_wlm": true,
    "concurrency_scaling": "off",
    "priority": "low"
  }
]
```

### Manual WLM configuration (legacy)

```json
[
  {
    "queue_name": "priority-queries",
    "max_concurrency_slots": 15,
    "memory_percent": 40,
    "priority": "highest",
    "concurrency_scaling": "auto",
    "user_group": ["dashboard_users"]
  },
  {
    "queue_name": "etl",
    "max_concurrency_slots": 10,
    "memory_percent": 35,
    "priority": "normal",
    "query_group": ["batch_etl"]
  },
  {
    "queue_name": "ad-hoc",
    "max_concurrency_slots": 5,
    "memory_percent": 25,
    "priority": "low"
  }
]
```

**Rules:**
- `memory_percent` MUST sum to 100 across all queues.
- `max_concurrency_slots` determines parallel query count per queue.
- More slots = more parallelism but less memory per slot.
- Auto WLM ignores `max_concurrency_slots` and `memory_percent`.

### SQA configuration fields

| Field | Values | Default | Notes |
|---|---|---|---|
| `short_query_queue_enable` | true / false | false | Enables SQA |
| `max_execution_time` | 0-300 (seconds) | 120 | Queries estimated to complete within this threshold are routed to SQA |

### QMR rule schema

```json
{
  "rule_name": "runaway-cpu-log",
  "predicate": "cpu_time > 50000000000",
  "action": "log",
  "metadata": {"notes": "Log queries using >50s CPU"}
}
```

| Field | Description |
|---|---|
| `rule_name` | Unique rule identifier |
| `predicate` | Condition on STL_QUERY_METRICS columns |
| `action` | `log`, `hop`, or `abort` |

## STL_QUERY_METRICS column reference

| Column | Unit | Description |
|---|---|---|
| `userid` | — | User ID |
| `query` | — | Query ID |
| `service_class` | — | WLM queue (service class) ID |
| `cpu_time` | microseconds | Total CPU time |
| `scan_row_count` | rows | Rows scanned |
| `return_row_count` | rows | Rows returned to client |
| `nested_loop_join_row_count` | rows | Rows from nested loop joins (inefficient) |
| `hash_join_row_count` | rows | Rows from hash joins |
| `merge_join_row_count` | rows | Rows from merge joins |
| `elapsed_time` | microseconds | Wall-clock execution time |
| `queue_time` | microseconds | Time spent waiting in queue |
| `memory_to_percent` | percent | Memory usage vs. allocation |

## SQA threshold tuning guide

The `max_execution_time` parameter controls which queries SQA handles.

| Workload pattern | Recommended `max_execution_time` | Rationale |
|---|---|---|
| Dashboard lookups + heavy ETL | 60-120 | Short lookups bypass ETL queue |
| Mixed operational + reporting | 120 (default) | Balanced threshold |
| Mostly short queries, occasional long | 30-60 | Prevents long queries from stealing SQA slots |
| All long-running (batch) | Disable SQA | No short queries to isolate |

**Validation:** Check `STL_QUERY_METRICS` for the workload's p95
`elapsed_time`. Set `max_execution_time` to p95 of short queries × 2.
If no queries complete within the threshold, SQA never fires.

## AQUA acceleration patterns

| Query pattern | AQUA acceleration? | Notes |
|---|---|---|
| `LIKE '%pattern%'` on large VARCHAR | YES | Pushes regex to storage layer |
| `REGEXP_LIKE(col, 'pattern')` | YES | |
| Hash join on VARCHAR columns | YES | |
| UDF on scanned data | YES | |
| `SUM(revenue) GROUP BY date` | NO | Numeric aggregation — not AQUA-accelerated |
| `WHERE date > '2026-01-01'` | NO | Date filtering — not AQUA-accelerated |
| `JOIN ON a.id = b.id` (integer) | NO | Integer equality join — not AQUA-accelerated |

**Enable AQUA:**
```bash
aws redshift modify-cluster \
  --cluster-identifier <cluster-id> \
  --aqua-configuration-status enabled
```

Requires cluster reboot. Schedule in maintenance window.

## Materialized view refresh intervals

| Workload | Refresh interval | Cost impact |
|---|---|---|
| Executive dashboard (hourly base data) | 5-15 minutes | Sub-1% of cluster compute |
| Daily summary report | 1-4 hours | Negligible |
| Near-real-time operational dashboard | 1-5 minutes | 1-3% of cluster compute |

**Monitor refresh state:**
```sql
SELECT * FROM sys_mv_refresh_history
ORDER BY start_time DESC LIMIT 20;
```

## COPY command options reference

| Option | Default | When to change |
|---|---|---|
| `COMPUPDATE` | ON (first load) | Turn OFF for incremental loads on tables with established encodings |
| `MAXROWS` | 100000 per batch | Increase for tables with many sort keys; decrease for wide rows |
| `MAXERROR` | 0 | Increase for tolerance to bad rows (log to STL_LOAD_ERRORS) |
| `STATUPDATE` | OFF | Turn ON for first load to set table statistics |
| `IGNOREHEADER` | 0 | Set to 1 for CSV files with header row |

**S3 file splitting for parallel COPY:**
- Minimum: 1 file per cluster slice.
- Optimal: multiples of slice count for maximum parallelism.
- `ra3.16xlarge` with 4 nodes = 32 slices → split into 32, 64, or 128 files.

## Regional pricing multipliers

Approximate multiplier vs us-east-1 for Redshift RA3 node types.

| Region | Multiplier | Notes |
|---|---|---|
| us-east-1, us-east-2, us-west-2 | 1.00x | Baseline |
| us-west-1 | 1.05x | Slight premium |
| eu-west-1, eu-west-2, eu-central-1 | 1.10-1.15x | EU premium |
| ap-southeast-1, ap-southeast-2 | 1.12-1.18x | APAC premium |
| ap-northeast-1 (Tokyo) | 1.10-1.15x | |
| ap-south-1 (Mumbai) | 1.15-1.25x | |
| sa-east-1 (São Paulo) | 1.35-1.50x | Highest premium |

Always re-check via the AWS Pricing API for production estimates.

## CLI quick reference

### Describe cluster configuration
```bash
aws redshift describe-clusters --cluster-identifier <id> \
  --query 'Clusters[0].{NodeType:NodeType,NumberOfNodes:NumberOfNodes,ClusterParameterGroups:ClusterParameterGroups}' \
  --output json

aws redshift describe-cluster-configuration --cluster-identifier <id> \
  --output json
```

### Query STL tables via Data API
```bash
aws redshift-data execute-statement \
  --cluster-identifier <id> \
  --database <db> \
  --db-user <user> \
  --sql "SELECT query, elapsed, cpu_time FROM STL_QUERY ORDER BY elapsed DESC LIMIT 50"
```

### Modify WLM via parameter group
```bash
aws redshift modify-cluster-parameter-groups \
  --parameter-group-name <group> \
  --parameters \
    ParameterName=auto_wlm,ParameterValue=true \
    ParameterName=wlm_json_configuration,ParameterValue='[{"auto_wlm":true,"concurrency_scaling":"auto","short_query_queue_enable":true,"max_execution_time":120}]'

aws redshift modify-cluster \
  --cluster-identifier <id> \
  --cluster-parameter-group-name <group>
```

### CloudWatch metrics
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Redshift \
  --metric-name WLMQueueLength \
  --dimensions Name=ClusterIdentifier,Value=<id> \
  --start-time $(date -u -d '-30 days' +%FT%TZ) \
  --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json
```
