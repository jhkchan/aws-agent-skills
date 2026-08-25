# Redshift Diagnostic SQL and CLI Reference

Supplementary reference for the Redshift Query Troubleshooter skill.
A curated SQL and CLI command catalog for each diagnostic layer, mapped
to the decision tree in SKILL.md.

## Layer 1: Query history and status

```sql
-- Recent queries
SELECT userid, query, pid, starttime, endtime,
       elapsed / 1000000 AS elapsed_secs,
       aborted, label
FROM stl_query
WHERE starttime >= CURRENT_DATE - INTERVAL '1 hour'
ORDER BY starttime DESC
LIMIT 20;

-- Currently executing queries
SELECT pid, query, starttime, elapsed / 1000000 AS elapsed_secs
FROM stv_inflight
ORDER BY starttime;

-- Query text for a specific query ID
SELECT query, sequence, text
FROM stl_querytext
WHERE query = <query_id>
ORDER BY sequence;
```

## Layer 2: WLM queue analysis

```sql
-- WLM timing per query
SELECT query, service_class, service_class_name,
       queue_time / 1000000 AS queue_secs,
       exec_time / 1000000 AS exec_secs,
       total_queue_time / 1000000 AS total_queue_secs,
       total_exec_time / 1000000 AS total_exec_secs,
       state
FROM stl_wlm_query
WHERE query = <query_id>;

-- WLM service class configuration
SELECT service_class, name, num_query_tasks,
       max_execution_time / 1000000 AS max_exec_secs,
       query_queue_time_threshold / 1000000 AS queue_threshold_secs
FROM stv_wlm_service_class_config
WHERE service_class >= 6;

-- Current queue state (queries waiting and executing)
SELECT service_class, num_executing, num_queued_waiting,
       num_wlm_rules_executed
FROM stv_wlm_service_class_state
WHERE service_class >= 6;
```

## Layer 3: Table lock detection

```sql
-- All active locks with table names
SELECT t.owner AS owner_pid,
       c.relname AS table_name,
       t.pid AS locked_pid,
       t.txn_owner,
       t.xid,
       t.granted,
       t.lock_mode,
       t.lock_owner_pid AS blocking_pid
FROM stv_locks t
JOIN pg_class c ON c.oid = t.relation
ORDER BY t.granted, t.relation;

-- What each blocked/blocking PID is executing
SELECT pid, query, starttime, elapsed / 1000000 AS elapsed_secs
FROM stv_inflight
WHERE pid IN (
  SELECT pid FROM stv_locks WHERE granted = true
  UNION
  SELECT lock_owner_pid FROM stv_locks WHERE granted = false
);

-- Recent deadlocks
SELECT d.deadlock_id, d.pid, d.xid, d.lock_mode,
       t.relname, d.query
FROM stl_ddltext d
JOIN pg_class t ON true
WHERE d.pid IN (
  SELECT pid FROM stl_tr_conflict
  WHERE starttime >= CURRENT_DATE - INTERVAL '1 day'
);
```

## Layer 4: COPY / load errors

```sql
-- Recent load errors (most detailed)
SELECT userid, slice, tbl, starttime, errcode, errmsg,
       filename, line_number, colname, coltype,
       raw_line, raw_field_value
FROM stl_load_errors
WHERE starttime >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY starttime DESC
LIMIT 20;

-- Recent COPY commands and their status
SELECT query, userid, database, tablename, filename,
       start_time, end_time, status, line_count,
       empty_line_count, field_count
FROM stl_load_commits
WHERE start_time >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY start_time DESC
LIMIT 20;

-- Check cluster IAM roles (via CLI)
-- aws redshift describe-clusters --cluster-identifier <id> \
--   --query 'Clusters[0].IamRoles' --output json
```

## Layer 5: Distribution and sort key analysis

```sql
-- Table metadata overview
SELECT schemaname, tablename, diststyle, sortkey1,
       size, pct_used, max_skew, unsorted, tbl_rows
FROM svv_table_info
WHERE schemaname NOT IN ('pg_catalog', 'pg_internal')
ORDER BY size DESC
LIMIT 30;

-- Column-level distkey and sortkey info
SELECT tablename, "column", type, encoding,
       distkey, sortkey, sortkey_order
FROM pg_table_def
WHERE schemaname = '<schema>' AND tablename = '<table>'
ORDER BY sortkey NULLS LAST;

-- Distribution skew per slice
SELECT slice, COUNT(*) AS row_count
FROM <table_name>
GROUP BY slice
ORDER BY slice;

-- Tables with high skew
SELECT schemaname, tablename, diststyle, max_skew
FROM svv_table_info
WHERE max_skew > 1.5
ORDER BY max_skew DESC;
```

## Layer 6: EXPLAIN and query plan analysis

```sql
-- Get the EXPLAIN plan for a specific query
EXPLAIN
<paste the query here>;

-- SVV_QUERY_SUMMARY for a completed query
SELECT query, segment, step, maxtime, avgtime,
       rows, bytes, is_diskbased
FROM svv_query_summary
WHERE query = <query_id>
ORDER BY segment, step;

-- STL_PLAN_INFO (operation types per step)
SELECT query, node_id, operation_type, location
FROM stl_plan_info
WHERE query = <query_id>
ORDER BY node_id;
```

## Layer 7: Connection and SSL analysis

```sql
-- Active sessions
SELECT user_name, db_name, pid, type, recordtime,
       remote_host, remote_port
FROM stv_sessions
ORDER BY recordtime DESC;

-- Connection count
SELECT COUNT(*) AS total_connections FROM stv_sessions;

-- Connections per database
SELECT db_name, COUNT(*) AS num_connections
FROM stv_sessions
GROUP BY db_name;

-- Connections per user
SELECT user_name, COUNT(*) AS num_connections
FROM stv_sessions
GROUP BY user_name;

-- Recent connection log (auth, disconnect events)
SELECT event, recordtime, remote_host, remote_port,
       db_name, user_name, pid
FROM stl_connection_log
WHERE recordtime >= CURRENT_DATE - INTERVAL '1 hour'
ORDER BY recordtime DESC
LIMIT 50;

-- SSL setting (via CLI)
-- aws redshift describe-cluster-parameters
--   --parameter-group-name <pg-name> --output json
--   --query 'Parameters[?ParameterName==`require_ssl`]'
```

## Layer 8: Vacuum analysis

```sql
-- Active vacuum progress
SELECT * FROM svv_vacuum_progress;

-- Tables needing vacuum (high unsorted)
SELECT schemaname, tablename, unsorted, size, tbl_rows
FROM svv_table_info
WHERE unsorted > 5
ORDER BY unsorted DESC;

-- Recent vacuum history
SELECT table_name, status, sort_type, rows, mb,
       elapsed_secs
FROM stl_vacuum
WHERE starttime >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY starttime DESC
LIMIT 20;

-- Concurrent writes blocking vacuum
SELECT t.relation, c.relname, t.pid, t.lock_mode,
       t.granted, t.lock_owner_pid
FROM stv_locks t
JOIN pg_class c ON c.oid = t.relation
WHERE t.granted = true
  AND c.relname = '<table_being_vacuumed>';
```

## Layer 9: Encoding analysis

```sql
-- Server and client encoding
SHOW server_encoding;
SHOW client_encoding;

-- Set client encoding for the session
SET client_encoding TO 'UTF8';
SET client_encoding TO 'LATIN1';
```

## Layer 10: Cluster configuration (CLI)

```bash
# Cluster details (node type, status, parameter groups)
aws redshift describe-clusters \
  --cluster-identifier <id> --output json

# Parameter group values (WLM, SSL, etc.)
aws redshift describe-cluster-parameters \
  --parameter-group-name <pg-name> --output json

# Cluster subnet groups (network)
aws redshift describe-cluster-subnet-groups \
  --cluster-subnet-group-name <name> --output json

# Security groups
aws redshift describe-cluster-security-groups \
  --output json

# Execute SQL via Data API (no JDBC/ODBC needed)
aws redshift-data execute-statement \
  --cluster-identifier <id> \
  --database <db> \
  --db-user <user> \
  --sql "EXPLAIN SELECT ..."
  --output json

# Check Data API statement status
aws redshift-data describe-statement \
  --id <statement-id> --output json
```

## Common error code reference

| Error code | Meaning | Likely layer |
|---|---|---|
| 1204 | Delimiter not found | COPY_DATA_FORMAT |
| 1206 | Missing column value | COPY_DATA_FORMAT |
| 1216 | Invalid digit / numeric format | COPY_DATA_FORMAT |
| 1224 | Extra column(s) found | COPY_DATA_FORMAT |
| 1230 | Character not in repertoire | ENCODING_CONVERSION |
| 8001 | S3ServiceException | COPY_IAM_ROLE |
| 25P02 | Transaction aborted (deadlock) | TABLE_LOCK |
| 53400 | Configuration limit exceeded | CONNECTION_LIMIT |
| 28000 | Authentication failed | SSL_TLS_ERROR / config |
| XX000 | Internal error | Escalate to AWS Support |

## Account-wide pre-flight commands (from SKILL.md)

```sql
-- 1. Cluster-level info (via CLI)
-- aws redshift describe-clusters --cluster-identifier <id> --output json

-- 2. Recent queries and their status
SELECT userid, query, pid, starttime, endtime, elapsed,
       aborted, label
FROM stl_query
WHERE starttime >= CURRENT_DATE - INTERVAL '1 hour'
ORDER BY starttime DESC
LIMIT 20;

-- 3. WLM query state (which queue, wait time)
SELECT query, service_class, service_class_name,
       queue_time, exec_time, state
FROM stl_wlm_query
WHERE query IN (
  SELECT query FROM stl_query
  WHERE starttime >= CURRENT_DATE - INTERVAL '1 hour'
)
ORDER BY query DESC;

-- 4. Active locks
SELECT t.owner, t.relation, t.pid, t.txn_owner, t.xid,
       c.relname, t.granted, t.lock_mode, t.lock_owner_pid
FROM stv_locks t
JOIN pg_class c ON c.oid = t.relation
ORDER BY t.granted, t.relation;

-- 5. Table info (distribution, sort keys, size, skew)
SELECT schemaname, tablename, diststyle, sortkey1, size,
       pct_used, max_skew, unsorted
FROM svv_table_info
WHERE schemaname NOT IN ('pg_catalog', 'pg_internal')
ORDER BY size DESC
LIMIT 20;

-- 6. Load errors (COPY failures)
SELECT userid, slice, tbl, starttime, errcode, errmsg,
       colname, coltype, raw_line, raw_field_value
FROM stl_load_errors
WHERE starttime >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY starttime DESC
LIMIT 10;
```


## Query-state short-circuit (from SKILL.md)

| `stl_query` status | Effect on diagnosis |
|---|---|
| `aborted = 0`, `endtime` populated | Query completed. If slow, investigate query plan. |
| `aborted = 1`, `starttime` + `endtime` present | Query was cancelled. Check `stl_wlm_query` for WLM timeout, or `stl_eventlog` for user-initiated cancel. |
| `endtime` is NULL, `starttime` is recent | Query is currently running. Check `stv_inflight` for the current step and `stv_locks` for blocking locks. |
| `elapsed` is very large | Query ran to completion but took a long time. Investigate EXPLAIN plan, distribution, and sort keys. |


## Step 2 — WLM queue probes and key distinctions (from SKILL.md)

```sql
-- Check WLM queue assignment and timing
SELECT q.query, q.service_class, q.service_class_name,
       q.queue_time / 1000000 AS queue_time_secs,
       q.exec_time / 1000000 AS exec_time_secs,
       q.total_queue_time / 1000000 AS total_queue_secs,
       q.total_exec_time / 1000000 AS total_exec_secs,
       q.state
FROM stl_wlm_query q
WHERE q.query = <query_id>;

-- Check the WLM configuration
SELECT service_class, name, num_query_tasks, max_execution_time,
       query_queue_time_threshold
FROM stv_wlm_service_class_config
WHERE service_class >= 6;
```

Key distinctions:
- **`queue_time` >> `exec_time`**: The query spent most of its time
  waiting in the queue. The queue was overloaded. Fix: add slots,
  route the query to a different queue, or reduce concurrent query
  volume.
- **`exec_time` >> `queue_time`**: The query was slow during execution
  and hit the execution timeout. Fix: optimize the query plan
  (distribution, sort keys).
- **`total_queue_time` is large with multiple `service_class` values**:
  The query hopped between queues (WLM Query Queue Hopping). It timed
  out in one queue and was moved to the next.

## Step 3 — lock probes (from SKILL.md)

```sql
-- Active locks
SELECT t.owner AS owner_pid,
       c.relname AS table_name,
       t.pid AS locked_pid,
       t.txn_owner,
       t.xid,
       t.granted,
       t.lock_mode,
       t.lock_owner_pid AS blocking_pid
FROM stv_locks t
JOIN pg_class c ON c.oid = t.relation
ORDER BY t.granted, t.relation;

-- What is each holding/ blocked PID executing?
SELECT pid, query, starttime, elapsed/1000000 AS elapsed_secs
FROM stv_inflight
WHERE pid IN (
  SELECT pid FROM stv_locks WHERE granted = true
  UNION
  SELECT lock_owner_pid FROM stv_locks WHERE granted = false
);
```

## Step 4a — STL_LOAD_ERRORS probe (from SKILL.md)

```sql
SELECT userid, slice, tbl, starttime, errcode, errmsg,
       filename, line_number, colname, coltype,
       raw_line, raw_field_value
FROM stl_load_errors
WHERE starttime >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY starttime DESC
LIMIT 20;
```

## Step 4b — IAM role verification (from SKILL.md)

```sql
-- Verify the cluster's IAM roles
-- Via CLI:
-- aws redshift describe-clusters --cluster-identifier <id> \
--   --query 'Clusters[0].IamRoles' --output json
```

## Step 4d — manifest verification (from SKILL.md)

```sql
-- Verify the manifest file exists and is valid JSON
-- The manifest must have entries like:
-- {"entries": [{"url": "s3://bucket/path/file.csv", "mandatory": true}]}
```

## Step 5 — distribution/skew probes (from SKILL.md)

```sql
-- Check distribution styles of joined tables
SELECT schemaname, tablename, diststyle
FROM svv_table_info
WHERE tablename IN ('<table1>', '<table2>');

-- Check skew per slice
SELECT slice, num_values, MIN(num_values) OVER () AS min_vals,
       MAX(num_values) OVER () AS max_vals
FROM (
  SELECT slice, COUNT(*) AS num_values
  FROM <table_name>
  GROUP BY slice
) t;
```

## Step 6 — sort key probes (from SKILL.md)

```sql
-- Check sort keys
SELECT schemaname, tablename, sortkey1, sortkey1_enc,
       size, unsorted
FROM svv_table_info
WHERE tablename IN ('<table1>', '<table2>');

-- Check the actual sort key columns
SELECT tablename, "column", type, encoding, distkey, sortkey
FROM pg_table_def
WHERE schemaname = '<schema>' AND tablename = '<table>'
ORDER BY sortkey;
```

## Step 6 — sort key change SQL (from SKILL.md)

```sql
-- Change sort key (requires table rewrite)
ALTER TABLE <table> ALTER SORTKEY (sale_date);
-- Or create a new table with the right sort key and copy data
```

## Step 7 — EXPLAIN probe (from SKILL.md)

```sql
-- Get the EXPLAIN output
EXPLAIN
SELECT ... <the query> ...;
```

## Step 8 — connection probes (from SKILL.md)

```sql
-- Total active connections
SELECT COUNT(*) FROM stv_sessions;

-- Connections per database
SELECT db_name, COUNT(*) AS num_connections
FROM stv_sessions
GROUP BY db_name;

-- Connections per user
SELECT user_name, COUNT(*) AS num_connections
FROM stv_sessions
GROUP BY user_name;
```

## Step 9 — SSL parameter probe (from SKILL.md)

```sql
-- Check cluster parameter group for SSL requirement
-- Via CLI:
-- aws redshift describe-cluster-parameters
--   --parameter-group-name <pg-name> --output json
--   --query 'Parameters[?ParameterName==`require_ssl`]'
```

## Step 10 — vacuum probes (from SKILL.md)

```sql
-- Check vacuum progress
SELECT * FROM svv_vacuum_progress;

-- Check table statistics (unsorted percentage)
SELECT schemaname, tablename, unsorted, size
FROM svv_table_info
WHERE unsorted > 5
ORDER BY unsorted DESC;

-- Check for concurrent writes blocking the vacuum
SELECT t.relation, c.relname, t.pid, t.lock_mode, t.granted
FROM stv_locks t
JOIN pg_class c ON c.oid = t.relation
WHERE t.granted = true;
```

## Step 11 — encoding probes (from SKILL.md)

```sql
-- Check server encoding
SHOW server_encoding;

-- Check client encoding
SHOW client_encoding;
```

## System table quick reference (from SKILL.md)

### System table quick reference

| Table | Purpose |
|---|---|
| `STL_QUERY` | Query history (text, start/end time, status) |
| `STL_WLM_QUERY` | WLM queue assignment and timing per query |
| `STV_LOCKS` | Active table locks |
| `STV_INFLIGHT` | Currently executing queries |
| `STL_LOAD_ERRORS` | COPY error details |
| `STL_ERROR` | General error log |
| `SVV_TABLE_INFO` | Table metadata (diststyle, sortkey, size, skew) |
| `SVV_QUERY_SUMMARY` | Per-query step execution summary |
| `PG_TABLE_DEF` | Column-level metadata (distkey, sortkey, encoding) |
| `SVV_VACUUM_PROGRESS` | Active vacuum progress |
| `STV_WLM_SERVICE_CLASS_CONFIG` | WLM queue configuration |
