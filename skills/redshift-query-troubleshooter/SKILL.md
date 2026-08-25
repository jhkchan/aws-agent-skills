---
name: redshift-query-troubleshooter
description: 'Diagnoses Amazon Redshift query failures through a twelve-category diagnostic tree: WLM queue timeout (queue wait vs execution time), table lock detection (STV_LOCKS, lock contention), COPY command failures (IAM role, data format, delimiter, S3 manifest mismatch), distribution key skew causing data skew, sort key misalignment causing full table scans, nested loop joins (DS_DIST_NONE vs DS_DIST_ALL_INNER), insufficient sort/dist keys, STL_ERROR messages, connection limits, SSL/TLS certificate issues, query plan analysis (EXPLAIN), vacuum blocked by concurrent writes, and encoding conversion errors. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and query context. Live-account diagnosis uses aws redshift describe-clusters, aws redshift describe-cluster-subnet-groups, aws redshift-data execute-statement / describe-statement, and SQL queries against system tables (STV_LOCKS, STL_ERROR, SVV_QUERY_SUMMARY, STL_QUERY, STL_LOAD_ERRORS, SVV_TABLE_INFO, PG_TABLE_DEF, STV_WLM_QUERY_STATE) via the...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an Amazon Redshift query failure (WLM queue timeout, table lock contention, COPY command failure, distribution key skew, sort key misalignment, nested loop join, connection limit, SSL/TLS error, vacuum blocked, or encoding conversion error), walking a symptom to the failed config or data-modeling layer with verify and fix commands.
  when_not_to_use: Amazon RDS/Aurora query performance tuning (use RDS-specific tooling), Athena query failures (use athena-query-optimizer), EMR Spark job debugging (use emr-cluster-auditor), application-side ORM query construction (use the application logs and ORM docs), or Redshift Serverless workgroup provisioning (use redshift-specific infrastructure tooling). This skill diagnoses query-time failures; it does not tune cluster sizing or manage resize operations.
  activation_triggers: Redshift query timeout, WLM queue timeout, Redshift table lock, STV_LOCKS, Redshift COPY command failure, STL_LOAD_ERRORS, distribution key skew, sort key misalignment, full table scan, nested loop join, DS_DIST_ALL_INNER, DS_DIST_NONE, Redshift connection limit, Redshift SSL certificate, Redshift encoding conversion, Redshift vacuum blocked, SVV_QUERY_SUMMARY, STL_ERROR, Redshift query plan, EXPLAIN, S3 COPY manifest mismatch, troubleshoot Redshift query
  invocation_schema: 'Input: either (a) a symptom description (error message, observed behaviour, "query times out", "COPY fails", "query is slow"), optionally paired with the query text and cluster context, OR (b) a cluster identifier plus query ID or error message for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {WLM_QUEUE_TIMEOUT, TABLE_LOCK, COPY_IAM_ROLE, COPY_DATA_FORMAT, DIST_KEY_SKEW, SORT_KEY_MISALIGNMENT, NESTED_LOOP_JOIN, CONNECTION_LIMIT, SSL_TLS_ERROR, VACUUM_BLOCKED, ENCODING_CONVERSION, QUERY_PLAN, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "Redshift query on sales table takes 45 seconds; EXPLAIN

    shows ds_dist_all_inner and a seq scan. The table uses DISTSTYLE EVEN

    but joins on store_id which is the dist key of the store table."

    Cluster: prod-analytics-cluster

    Database: analytics_db

    Query: SELECT s.store_name, sum(sa.amount) FROM store s JOIN sales sa ON s.store_id = sa.store_id GROUP BY s.store_name

    Table sales: DISTSTYLE EVEN, sort key (sale_date)

    Table store: DISTSTYLE KEY (distkey: store_id), sort key (store_id)

    EXPLAIN excerpt: XN Hash Join DS_DIST_ALL_INNER -> XN Seq Scan on sales'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Redshift, WLM, WLM queue timeout, table lock, STV_LOCKS, COPY command, distribution key, distribution style, sort key, data skew, nested loop join, DS_DIST_ALL_INNER, full table scan, STL_ERROR, SVV_QUERY_SUMMARY, EXPLAIN, vacuum, connection limit, SSL certificate, encoding conversion, load error, S3 manifest, troubleshooting
  tags: redshift, analytics, troubleshooting, wlm, distribution-key, sort-key, query-performance, data-warehouse
---

# Redshift Query Troubleshooter

## Quick start

- **Symptom -> layer map (first plausible match drives the first probe):**
  Query cancelled after N seconds -> WLM_QUEUE_TIMEOUT; query hangs
  and never completes -> TABLE_LOCK; COPY fails with error ->
  COPY_IAM_ROLE / COPY_DATA_FORMAT; query is slow but completes ->
  DIST_KEY_SKEW / SORT_KEY_MISALIGNMENT / NESTED_LOOP_JOIN; cannot
  connect -> CONNECTION_LIMIT / SSL_TLS_ERROR; characters garbled or
  "character not in repertoire" -> ENCODING_CONVERSION; VACUUM runs
  forever -> VACUUM_BLOCKED.
- **Always verify with a probe, never guess.** Each layer has a
  diagnostic query or CLI command that proves or disproves it. A
  ROOT_CAUSE_IDENTIFIED verdict requires positive evidence -- a
  failing probe that matches the symptom -- not a process of
  elimination.
- **Distribution style determines join co-location.** The most common
  Redshift performance problem is a join between two tables on
  different distribution styles where the join column is not the
  dist key on at least one table, forcing a DS_DIST_ALL_INNER
  (broadcast or redistribute). Always EXPLAIN the query and check
  the scan type before tuning anything else.
- **Sort keys enable zone map elimination.** A table with no sort key
  or a sort key that does not match the query predicate forces a full
  sequential scan (Seq Scan). With a matching sort key, Redshift uses
  zone maps to skip entire 1 MB blocks. A 10x scan reduction is
  common just from adding the right sort key.
- **WLM queue timeout is NOT execution timeout.** A WLM queue timeout
  means the query waited too long in the queue (QCU spent) and was
  cancelled before it started executing. A long-running query that
  starts but takes too long is a different problem (query plan,
  distribution, or sort key issue).

## Mindset

A failing or slow Redshift query is usually a data modelling or
workload management problem wearing a SQL costume. The SQL is correct
in the majority of cases; the broken thing is the distribution key,
sort key, WLM queue assignment, table lock, or COPY configuration.
Treat the query text as innocent until the distribution style, sort
key, query plan, and WLM configuration are proven correct. Senior
data engineers do not start by rewriting the SQL; they start with
`EXPLAIN`, `SVV_QUERY_SUMMARY`, and `SVV_TABLE_INFO`, and only modify
the query once the physical design and workload management are
confirmed correct.

## Philosophy

Four behaviours separate a senior Redshift engineer from a generalist:

- **The EXPLAIN output's scan type tells you the problem.** A `Seq
  Scan` means a full table scan -- no sort key elimination. A
  `DS_DIST_NONE` means the join is co-located -- no network
  redistribution. A `DS_DIST_ALL_INNER` means the inner table is
  broadcast to all nodes -- a costly operation on large tables. An
  `XN Nested Loop` means a Cartesian product -- almost always a
  missing join condition. These three signals eliminate 80% of
  performance diagnosis.

- **Distribution style (KEY vs ALL vs EVEN) is a join-time decision.**
  `DISTSTYLE KEY` on the join column co-locates matching rows on the
  same slice, enabling `DS_DIST_NONE` joins. `DISTSTYLE ALL`
  replicates the full table to every node (good for small dimension
  tables, bad for large fact tables). `DISTSTYLE EVEN` distributes
  randomly -- joins always require redistribution. Choosing the wrong
  distribution style for the workload's dominant join pattern is the
  #1 cause of slow queries.

- **Sort keys are for range elimination, not just ordering.** A sort
  key on `sale_date` enables Redshift's zone maps to skip 1 MB blocks
  that fall outside the query's date range. Without a sort key on the
  filter column, every query scans the entire table. The sort key
  should match the column most frequently used in range predicates
  (WHERE, BETWEEN, >=).

- **WLM queue hopping can hide queue timeout root causes.** With WLM
  Query Queue Hopping, a query that times out in one queue is
  automatically moved to the next queue. The query eventually succeeds
  (or times out in the last queue), but the operator sees a long total
  wait time. The root cause is the first queue being overloaded, not
  the query being slow.

## Quick reference -- symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `Query X cancelled due to queue timeout` | WLM_QUEUE_TIMEOUT | `STL_WLM_QUERY` for queue time vs execution time |
| Query hangs, never completes | TABLE_LOCK | `STV_LOCKS` for active locks |
| `COPY ... failed`, `stl_load_errors` | COPY_IAM_ROLE / COPY_DATA_FORMAT | `STL_LOAD_ERRORS` for error detail |
| Query slow, `DS_DIST_ALL_INNER` in EXPLAIN | DIST_KEY_SKEW | `EXPLAIN` + `SVV_TABLE_INFO` distribution style |
| Query slow, `Seq Scan` in EXPLAIN | SORT_KEY_MISALIGNMENT | `EXPLAIN` + `SVV_TABLE_INFO` sort key |
| `Nested Loop` in EXPLAIN | NESTED_LOOP_JOIN | `EXPLAIN` join conditions |
| `FATAL: too many connections` | CONNECTION_LIMIT | Cluster connection limit vs active connections |
| `SSL certificate verification failed` | SSL_TLS_ERROR | Cluster parameter group `require_ssl` |
| `character with byte sequence ... has no equivalent` | ENCODING_CONVERSION | Client encoding vs column encoding |
| `VACUUM` running for hours | VACUUM_BLOCKED | `SVV_VACUUM_PROGRESS` + concurrent write locks |
| `stl_error` entries | QUERY_PLAN / ENCODING_CONVERSION | `STL_ERROR` for error code and message |

## Pre-flight: cluster state and gather-info gate

Before running symptom-specific probes, gather the canonical cluster
configuration and short-circuit on states that mimic query failures.

### Account-wide pre-flight commands

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

### Query-state short-circuit

| `stl_query` status | Effect on diagnosis |
|---|---|
| `aborted = 0`, `endtime` populated | Query completed. If slow, investigate query plan. |
| `aborted = 1`, `starttime` + `endtime` present | Query was cancelled. Check `stl_wlm_query` for WLM timeout, or `stl_eventlog` for user-initiated cancel. |
| `endtime` is NULL, `starttime` is recent | Query is currently running. Check `stv_inflight` for the current step and `stv_locks` for blocking locks. |
| `elapsed` is very large | Query ran to completion but took a long time. Investigate EXPLAIN plan, distribution, and sort keys. |

If the input is malformed (missing cluster identifier, absent query
text or error message, no table context), emit:

```text
TARGET: <cluster-id or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context -- at minimum a symptom
  description (the error string or observed behaviour) and either the
  cluster identifier or the query text.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error message
  or observed symptom, (2) the cluster identifier and database name,
  (3) the query text or query ID, and (4) the table definitions
  (distribution style, sort key) for the tables involved.
```

## Process -- Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on
the observed symptom, then walk the layer-specific probes in order.
**Never emit ROOT_CAUSE_IDENTIFIED without a failing probe that
matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior Redshift engineer knows
from incident experience:

- **DISTSTYLE KEY requires the join column to be the dist key on BOTH
  tables.** A fact table distributed on `customer_id` joined to a
  dimension table distributed on `store_id` forces a network
  redistribution (DS_DIST_ALL_INNER or DS_DIST_OUTER). The fix is
  either making both tables KEY-distributed on the join column, or
  making the smaller table DISTSTYLE ALL.

- **DISTSTYLE ALL is not free.** An ALL-distributed table is fully
  replicated on every node. For a small dimension table (under ~2-5
  million rows), this is efficient -- joins are always local
  (DS_DIST_NONE). For a large table, ALL wastes storage and slows
  writes. Never use ALL on a fact table.

- **Compound sort keys are ordered.** A compound sort key on
  `(sale_date, store_id)` is only effective for queries that filter on
  `sale_date` or `sale_date AND store_id`. A query filtering on
  `store_id` alone gets NO sort key benefit because `store_id` is the
  second column. The first column of a compound sort key is always the
  most selective filter.

- **Interleaved sort keys are not magic.** An interleaved sort key on
  `(sale_date, store_id)` gives equal weight to both columns, enabling
  zone map elimination for queries filtering on either column alone.
  But interleaved sorts are expensive to maintain (VACUUM takes
  longer), and performance degrades with more than 3-4 interleaved
  columns.

- **WLM queue timeout counts queue wait, not execution time.** A
  query that spends 4 minutes waiting in the queue and 10 seconds
  executing is cancelled at the 4-minute mark if the WLM timeout is
  4 minutes. The fix is to reduce queue contention (add slots, tune
  queue assignment), not to optimize the query.

- **COPY requires the IAM role to have S3 read access.** The cluster's
  IAM role must have `s3:GetObject` on the bucket and path. A COPY
  that fails with "S3ServiceException: Access Denied" is always an
  IAM role issue, not a COPY syntax issue.

- **COPY from S3 manifest mismatch is subtle.** If the manifest file
  lists files that don't exist, or the manifest URL prefix is wrong,
  COPY fails with a load error that looks like a format error. Always
  verify the manifest contents separately.

- **STL_LOAD_ERRORS has one row per error, not per failed COPY.** A
  single COPY of a large file with multiple bad rows generates many
  STL_LOAD_ERRORS entries. Focus on the first error (lowest starttime)
  -- it usually identifies the root cause (wrong delimiter, wrong
  encoding, missing column).

- **Vacuum requires exclusive access to the table for the sort phase.**
  A VACUUM sorts the table to reclaim space and re-sort unsorted
  regions. If concurrent writes are occurring, the VACUUM may stall
  waiting for write locks. In busy clusters, schedule VACUUM during
  low-write windows.

- **Nested loop joins are almost always bugs.** A nested loop join
  (DS_DIST_NONE with no hash join) means Redshift could not find a
  join condition it could hash on. This usually means a missing join
  condition, a data type mismatch on the join column, or a join on a
  UDF output. The query plan shows `XN Nested Loop DS_DIST_NONE`.

- **Connection limits are cluster-level, not user-level.** The total
  number of connections is capped by the cluster's node count and
  type. Each connection consumes server-side resources. Connection
  pooling (via pgbouncer or a connection pooler) is essential for
  high-concurrency workloads.

- **Encoding conversion errors come from the client, not the data.** A
  "character with byte sequence ... has no equivalent in encoding"
  error means the client's encoding (e.g., UTF-8) cannot represent a
  character in the data's encoding (e.g., Latin-1). The fix is to set
  the client encoding to match the data, or to clean the data.

### Step 1: Symptom entry -- pick the diagnostic branch

Map the symptom to a branch. If none match, go to Step 12
(INSUFFICIENT_DATA).

| Symptom | Branch |
|---|---|
| Query cancelled, WLM timeout message | Step 2 -- WLM queue timeout |
| Query hangs, never completes | Step 3 -- Table lock |
| COPY command fails | Step 4 -- COPY failures |
| Query slow, EXPLAIN shows redistribution | Step 5 -- Distribution key skew |
| Query slow, EXPLAIN shows Seq Scan | Step 6 -- Sort key misalignment |
| EXPLAIN shows Nested Loop | Step 7 -- Nested loop join |
| Cannot connect, too many connections | Step 8 -- Connection limit |
| SSL/TLS error | Step 9 -- SSL/TLS |
| VACUUM runs forever | Step 10 -- Vacuum blocked |
| Encoding/character error | Step 11 -- Encoding conversion |
| None of the above | Step 12 -- INSUFFICIENT_DATA |

### Step 2: WLM queue timeout

Symptom: query is cancelled with a message like "Query X cancelled due
to queue timeout."

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

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: WLM_QUEUE_TIMEOUT`. Fix:
- Add query slots to the queue (`wlm_json_configuration`).
- Route long-running queries to a separate queue with higher timeout.
- Reduce the number of concurrent queries in the overloaded queue.

### Step 3: Table lock detection

Symptom: query hangs indefinitely, never completes or fails.

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

A lock with `granted = false` means the PID is waiting for a lock held
by `lock_owner_pid` (which has `granted = true`).

Common lock patterns:

| Pattern | Cause |
|---|---|
| Long-running SELECT blocking a COPY or INSERT | The SELECT holds a shared lock; the write needs an exclusive lock. |
| COPY blocking all queries on the table | COPY acquires an exclusive lock during load. Concurrent queries wait. |
| Two transactions deadlocking | Each holds a lock the other needs. Redshift detects and rolls back one. |
| VACUUM FULL blocking writes | VACUUM FULL requires exclusive access. Schedule during low-write windows. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TABLE_LOCK`. Fix:
- Identify and optionally terminate the blocking PID
  (`pg_terminate_backend(<pid>)`).
- For COPY lock contention: batch COPYs outside peak query hours.
- For VACUUM: schedule during low-write windows or use VACUUM DELETE
  (only reclaims deleted rows, lighter lock).

### Step 4: COPY command failures

Symptom: `COPY` command fails with a load error or access denied.

#### 4a: Check STL_LOAD_ERRORS

```sql
SELECT userid, slice, tbl, starttime, errcode, errmsg,
       filename, line_number, colname, coltype,
       raw_line, raw_field_value
FROM stl_load_errors
WHERE starttime >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY starttime DESC
LIMIT 20;
```

#### 4b: IAM role / S3 access

```sql
-- Verify the cluster's IAM roles
-- Via CLI:
-- aws redshift describe-clusters --cluster-identifier <id> \
--   --query 'Clusters[0].IamRoles' --output json
```

If the error is `S3ServiceException: Access Denied`, the cluster's IAM
role does not have `s3:GetObject` on the target bucket/prefix.

**ROOT_CAUSE_IDENTIFIED** with `LAYER: COPY_IAM_ROLE`. Fix: add
`s3:GetObject` on the bucket to the cluster's IAM role, or use
CREDENTIALS with explicit AWS access keys (not recommended).

#### 4c: Data format mismatch

Common COPY format errors:

| Error | Cause |
|---|---|
| `Delimiter not found` | Wrong DELIMITER (e.g., data is pipe-separated but COPY uses comma). |
| `Invalid digit, Value '.', Base 10` | Data has non-numeric values in a numeric column. Check `raw_field_value`. |
| `Character not in repertoire` | Encoding mismatch between the file and the COPY command. Add `ENCODING AS UTF8`. |
| `Extra column(s) found` | More columns in the data than the table. Add `FILLRECORD` / `FILLMISSING` or fix the data. |
| `Missing column(s)` | Fewer columns than the table. Check the file format. |

**ROOT_CAUSE_IDENTIFIED** with `LAYER: COPY_DATA_FORMAT`. Fix: correct
the COPY parameters (DELIMITER, ENCODING, FORMAT, FILLRECORD) based on
the `stl_load_errors` detail.

#### 4d: S3 manifest mismatch

If using `COPY FROM 's3://bucket/manifest.json' manifest`:

```sql
-- Verify the manifest file exists and is valid JSON
-- The manifest must have entries like:
-- {"entries": [{"url": "s3://bucket/path/file.csv", "mandatory": true}]}
```

If a mandatory file in the manifest does not exist, COPY fails. If
`mandatory: false` and the file is missing, COPY skips it silently
(the most common data-loss-via-COPY issue).

### Step 5: Distribution key skew

Symptom: query is slow. EXPLAIN shows `DS_DIST_ALL_INNER` or
`DS_BCAST_INNER` (broadcast of the inner table).

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

Key distribution patterns:

| Scenario | EXPLAIN shows | Root cause |
|---|---|---|
| Both tables KEY on join column | `DS_DIST_NONE` | Optimal -- no redistribution. |
| One table EVEN, other KEY | `DS_DIST_ALL_INNER` | EVEN table must be redistributed. Change to KEY on join column. |
| Both tables EVEN | `DS_DIST_ALL_INNER` | Both redistributed. Choose a dist key for both. |
| Small dimension table is KEY (not ALL) | `DS_DIST_ALL_INNER` | Change small table to DISTSTYLE ALL for DS_DIST_NONE. |
| Large fact table DISTSTYLE ALL | N/A (wastes storage) | Never use ALL on large tables. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DIST_KEY_SKEW`. Fix:
- Change the distribution style to KEY on the join column for both
  tables (`ALTER TABLE ... ALTER DISTSTYLE KEY (...)`).
- For small dimension tables (< 2-5M rows), use `DISTSTYLE ALL`.
- After changing, run ANALYZE to update table statistics.

### Step 6: Sort key misalignment

Symptom: query is slow. EXPLAIN shows `Seq Scan` on a large table
that should be using a range-restricted scan.

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

If `sortkey1` is empty or does not match the query's filter column:

| Sort key issue | Effect |
|---|---|
| No sort key | Every query is a full `Seq Scan`. Zone maps cannot eliminate blocks. |
| Sort key on wrong column | Zone maps exist but are useless for the query's actual filter. |
| Compound sort key, query filters on 2nd column | No zone map benefit; the first column of a compound key dominates. |
| `unsorted` is high (> 20%) | The table has many unsorted rows. Run VACUUM SORT to re-sort. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SORT_KEY_MISALIGNMENT`.
Fix: add or change the sort key to match the query's primary filter
column. For queries filtering on multiple independent columns,
consider an interleaved sort key (max 3-4 columns).

```sql
-- Change sort key (requires table rewrite)
ALTER TABLE <table> ALTER SORTKEY (sale_date);
-- Or create a new table with the right sort key and copy data
```

### Step 7: Nested loop join

Symptom: query is very slow. EXPLAIN shows `XN Nested Loop`.

```sql
-- Get the EXPLAIN output
EXPLAIN
SELECT ... <the query> ...;
```

A nested loop join means Redshift performs a Cartesian product --
every row in one table is matched against every row in another. This
is almost always a bug.

Common causes:

| Cause | Example |
|---|---|
| Missing join condition | `SELECT * FROM a, b WHERE a.x > 1` (no join between a and b) |
| Data type mismatch on join column | `a.id (int)` joined to `b.id (varchar)` -- no hash join possible |
| Join on a UDF output | `ON my_udf(a.x) = b.y` -- UDF output can't be hashed |
| Cross join intended but on large tables | `CROSS JOIN` on large tables; add a filter or redesign |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: NESTED_LOOP_JOIN`. Fix:
add the missing join condition, fix the data type mismatch, or
redesign the query to avoid the Cartesian product.

### Step 8: Connection limit

Symptom: `FATAL: too many connections for "<database>"` or
`FATAL: remaining connection slots are reserved for non-replication
superuser connections`.

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

The connection limit depends on the cluster's node count and type.
Each node supports a fixed number of connections (typically 500 per
node for most types, shared across all databases).

Common patterns:

| Pattern | Fix |
|---|---|
| Many short-lived connections from an app | Use a connection pooler (pgbouncer, RDS Proxy). |
| Long-running analytical sessions holding connections | Reduce idle session timeout; close connections after queries complete. |
| ETL tool opening many parallel connections | Limit parallelism in the ETL tool's config. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CONNECTION_LIMIT`. Fix:
implement connection pooling, reduce idle connections, or scale the
cluster to a larger node type with more connection capacity.

### Step 9: SSL/TLS certificate issues

Symptom: `SSL certificate verification failed` or
`FATAL: no pg_hba.conf entry for host ... SSL off`.

```sql
-- Check cluster parameter group for SSL requirement
-- Via CLI:
-- aws redshift describe-cluster-parameters
--   --parameter-group-name <pg-name> --output json
--   --query 'Parameters[?ParameterName==`require_ssl`]'
```

Common SSL issues:

| Issue | Fix |
|---|---|
| `require_ssl = true` but client does not use SSL | Enable SSL in the client connection string (`sslmode=require`). |
| Self-signed cert on non-prod cluster | Use `sslmode=verify-ca` (not `verify-full`) or add the cert to the trust store. |
| JDBC driver SSL handshake failure | Add `ssl=true&sslmode=require` to the JDBC URL. |
| Certificate expired after cluster cert rotation | Download the new cert from the AWS console and update the trust store. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SSL_TLS_ERROR`. Fix: align
the client SSL settings with the cluster's `require_ssl` parameter.

### Step 10: Vacuum blocked

Symptom: `VACUUM` command runs for a very long time without completing.

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

Common VACUUM issues:

| Issue | Fix |
|---|---|
| Concurrent writes holding locks | Schedule VACUUM during low-write windows. |
| Very large unsorted region | Run `VACUUM SORT ONLY` or increase maintenance window. |
| Table has many deleted rows | Run `VACUUM DELETE ONLY` (faster than full VACUUM). |
| `max_formatted_blocks` exceeded | The table's sorted region is too large for a single sort pass. Consider deep copy. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: VACUUM_BLOCKED`. Fix:
schedule VACUUM during low-write windows, use VACUUM DELETE ONLY or
SORT ONLY, or perform a deep copy (create a new table with the right
sort key and INSERT INTO).

### Step 11: Encoding conversion

Symptom: `ERROR: character with byte sequence 0xXX in encoding "UTF8"
has no equivalent in encoding "LATIN1"` or similar.

```sql
-- Check server encoding
SHOW server_encoding;

-- Check client encoding
SHOW client_encoding;
```

If the server encoding is UTF8 but the data contains characters not
representable in the client encoding (or vice versa), COPY and query
results fail with encoding errors.

Common fixes:

| Issue | Fix |
|---|---|
| COPY from a Latin-1 file into a UTF8 table | Add `ENCODING AS LATIN1` or convert the file to UTF8. |
| Client receiving UTF8 data but expecting Latin-1 | `SET client_encoding TO 'UTF8';` in the session. |
| Mixed-encoding data in one file | Clean the data; Redshift requires consistent encoding per COPY. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ENCODING_CONVERSION`.

### Step 12: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, emit:

```text
TARGET: <cluster-id>
VERDICT: INSUFFICIENT_DATA
REASON: The available evidence does not conclusively identify a
  single root cause from the diagnostic tree. List the probes already
  executed and their results, and request additional context.
LAYER: UNKNOWN
EVIDENCE:
  - <probes executed and results>
  - <missing information needed>
REMEDIATION: Provide (1) the EXPLAIN output for the failing query,
  (2) the SVV_TABLE_INFO for the tables involved, (3) the
  STL_WLM_QUERY entry for the query, and (4) the exact error message
  from STL_ERROR or the client.
```

## Output format

```text
TARGET: <cluster-id / query-id>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <WLM_QUEUE_TIMEOUT | TABLE_LOCK | COPY_IAM_ROLE |
        COPY_DATA_FORMAT | DIST_KEY_SKEW |
        SORT_KEY_MISALIGNMENT | NESTED_LOOP_JOIN |
        CONNECTION_LIMIT | SSL_TLS_ERROR | VACUUM_BLOCKED |
        ENCODING_CONVERSION | QUERY_PLAN | UNKNOWN>
EVIDENCE:
  - <observed symptom -- error string or behaviour>
  - <failing probe -- query/CLI and its output that confirms the cause>
  - <passing probes -- layers ruled out>
REMEDIATION:
  1. <specific action with SQL or CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing SQL or CLI, emit and
  await operator approval: "CONFIRM: About to <action> on <cluster>.
  Proceed? (yes/no)"
```

### Worked example -- distribution key skew (DS_DIST_ALL_INNER)

```text
TARGET: prod-analytics-cluster, query 12345
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The query joins sales (DISTSTYLE EVEN) to store (DISTSTYLE
  KEY on store_id) on the store_id column. EXPLAIN shows
  DS_DIST_ALL_INNER -- the sales table is redistributed to every
  node at query time because its distribution does not match the
  join column. The sales table has 800 million rows; the broadcast
  cost dominates query time.
LAYER: DIST_KEY_SKEW
EVIDENCE:
  - Symptom: query takes 45 seconds; EXPLAIN shows
    "XN Hash Join DS_DIST_ALL_INNER" followed by "XN Seq Scan on
    sales".
  - Probe: SVV_TABLE_INFO shows sales.diststyle = EVEN,
    store.diststyle = KEY(distkey: store_id). The join column
    (store_id) is not the dist key on sales.
  - Probe: EXPLAIN confirms DS_DIST_ALL_INNER -- the entire sales
    table is redistributed to all nodes.
  - Passing: sales has a sort key on sale_date; the query filters on
    sale_date (sort key is correct); the query uses a Hash Join (not
    a Nested Loop); no locks are present (STV_LOCKS empty); WLM
    queue time is < 1 second.
REMEDIATION:
  1. Change the sales table distribution style to KEY(store_id):
     ALTER TABLE sales ALTER DISTSTYLE KEY (store_id);
  2. Run ANALYZE to update statistics:
     ANALYZE sales;
  3. Re-run the query; EXPLAIN should show DS_DIST_NONE (no
    redistribution). Expected runtime: < 5 seconds.
CONFIRM: Before altering the table, emit and await:
  "CONFIRM: About to ALTER DISTSTYLE on sales to KEY(store_id).
   This requires a table rewrite. Proceed? (yes/no)"
```

### Worked example -- WLM queue timeout

```text
TARGET: prod-analytics-cluster, query 67890
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The query was cancelled after waiting 240 seconds in WLM
  service class 8 (Batch queue). The queue has 2 slots and 5
  concurrent queries were submitted simultaneously; only 2 could
  execute. The query's queue_time (240s) exceeds the queue's
  max_execution_time threshold.
LAYER: WLM_QUEUE_TIMEOUT
EVIDENCE:
  - Symptom: query cancelled with "Query 67890 cancelled due to
    queue timeout."
  - Probe: STL_WLM_QUERY shows queue_time = 240s, exec_time = 0s
    (never started executing), state = "cancelled".
  - Probe: STV_WLM_SERVICE_CLASS_CONFIG shows service_class 8 with
    num_query_tasks = 2, max_execution_time = 240000000 (240s).
  - Passing: EXPLAIN plan for the query is optimal (DS_DIST_NONE,
    sort key leveraged); no table locks; the query itself runs in
    3 seconds when it reaches the front of the queue.
REMEDIATION:
  1. Increase the Batch queue slots from 2 to 4:
     (via wlm_json_configuration parameter group update)
  2. Or route heavy analytical queries to a dedicated queue with
    more slots and a higher timeout.
  3. Verify by re-running the batch and checking STL_WLM_QUERY
    queue_time drops below 60s.
CONFIRM: Before modifying WLM config, emit and await:
  "CONFIRM: About to update WLM configuration on
   prod-analytics-cluster. Proceed? (yes/no)"
```

### Worked example -- COPY data format error

```text
TARGET: prod-analytics-cluster, COPY command at 14:23 UTC
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The COPY from s3://etl-bucket/daily/orders.csv failed.
  STL_LOAD_ERRORS shows errcode 1204 "Delimiter not found" at line
  1. The data file is pipe-delimited (|) but the COPY command
  specifies DELIMITER ','.
LAYER: COPY_DATA_FORMAT
EVIDENCE:
  - Symptom: COPY returns "stl_load_errors: Delimiter not found"
  - Probe: STL_LOAD_ERRORS shows raw_line =
    "1001|2024-01-15|450.00|shipped", errcode = 1204.
  - Probe: File header confirms pipe delimiter:
    order_id|order_date|amount|status
  - Passing: IAM role has s3:GetObject on the bucket (COPY_IAM_ROLE
    ruled out); file exists and is readable.
REMEDIATION:
  1. Update the COPY command delimiter:
     COPY orders FROM 's3://etl-bucket/daily/orders.csv'
       IAM_ROLE 'arn:aws:iam::111111111111:role/RedshiftETLRole'
       DELIMITER '|' FORMAT CSV;
  2. Or convert the data to comma-delimited before COPY.
  3. Verify by re-running COPY and checking STL_COMMUNICATIONS for
    successful load completion.
```

## Anti-Patterns -- NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is elsewhere.

- NEVER rewrite a slow query before running EXPLAIN. The EXPLAIN
  output's scan type (Seq Scan, DS_DIST_NONE, DS_DIST_ALL_INNER)
  immediately identifies whether the problem is distribution, sort
  keys, or join structure. Query rewrites without EXPLAIN are
  guesswork.

- NEVER use DISTSTYLE ALL on a large table. ALL replicates the entire
  table to every node. For tables over ~5 million rows, the storage
  and write-time cost is prohibitive. Use KEY on the join column
  instead.

- NEVER use DISTSTYLE EVEN for tables that participate in joins on a
  specific column. EVEN distribution means every join requires a
  network redistribution (DS_DIST_ALL_INNER). Choose KEY on the
  dominant join column.

- NEVER assume a compound sort key helps queries on its second column.
  A compound sort key on `(date, region)` only accelerates queries
  filtering on `date` or `date AND region`. A query filtering on
  `region` alone gets NO zone map benefit. Use an interleaved sort
  key for independent filter columns.

- NEVER ignore the `unsorted` column in SVV_TABLE_INFO. A high
  unsorted percentage (> 20%) means zone maps are degraded. Run
  VACUUM SORT to re-sort the table and restore zone map
  effectiveness.

- NEVER run COPY without checking STL_LOAD_ERRORS first. The first
  error row (lowest starttime) identifies the root cause -- wrong
  delimiter, wrong encoding, bad data value. Subsequent errors are
  often cascading failures from the first bad row.

- NEVER use `mandatory: false` on manifest files in production COPY
  pipelines without monitoring. Missing files are silently skipped,
  causing silent data loss. Use `mandatory: true` and alert on COPY
  failures.

- NEVER confuse WLM queue timeout with execution timeout. A query
  cancelled at 240s with queue_time = 240s and exec_time = 0s never
  ran -- it starved in the queue. Adding query slots fixes queue
  timeout; optimizing the query plan does not.

- NEVER assume a Nested Loop join is intentional. 99% of Nested Loop
  joins in analytical queries are bugs -- a missing join condition,
  a data type mismatch, or a join on a UDF output. Always flag
  Nested Loop joins as suspicious.

- NEVER terminate a blocking PID without confirming with the
  operator. `pg_terminate_backend` rolls back the target transaction.
  If the blocking query is a critical ETL load, terminating it may
  cause data inconsistency.

- NEVER change a table's distribution style during peak hours.
  `ALTER TABLE ... ALTER DISTSTYLE` requires a full table rewrite.
  On large tables this can take hours and holds exclusive locks.
  Schedule during maintenance windows.

- NEVER set the client encoding to a value that does not match the
  data encoding. UTF8 data loaded with a Latin-1 client encoding
  causes garbled characters and query failures. Always verify
  `SHOW client_encoding` matches the data source.

## Pre-flight safety checks (run before any state-changing SQL)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`ALTER TABLE`, `VACUUM`, `TRUNCATE`, `DROP TABLE`,
  `pg_terminate_backend`, WLM config update), emit and await operator
  approval. Do NOT execute until the operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`EXPLAIN`, `SELECT FROM stl_*`, `SELECT FROM svv_*`,
  `SHOW`). Do not perform state-changing operations as diagnostic
  probes.

- **`ALTER TABLE ... ALTER DISTSTYLE`** requires a full table rewrite.
  On large tables, this takes hours and holds an exclusive lock.
  Always schedule during maintenance windows. Verify with EXPLAIN
  after the rewrite.

- **`ALTER TABLE ... ALTER SORTKEY`** also requires a table rewrite.
  Same considerations as diststyle change.

- **`VACUUM`** holds locks that can block writes. `VACUUM DELETE ONLY`
  is lighter than full VACUUM. Always schedule during low-write
  windows.

- **`pg_terminate_backend(<pid>)`** rolls back the target transaction.
  Confirm the PID is not a critical ETL or reporting query before
  terminating.

- **WLM configuration changes** apply immediately to new queries;
  currently running queries are not affected. Test changes in a
  non-prod environment first.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple tables (e.g., all fact tables have
  EVEN distribution), batch `ALTER TABLE` operations one at a time
  with verification between each.

## Remediation guidance

### For WLM_QUEUE_TIMEOUT

- Add query slots to the overloaded queue (increase
  `num_query_tasks` in the WLM config).
- Route long-running queries to a dedicated queue with more slots.
- Reduce concurrent query volume (throttle ETL or reporting jobs).
- Consider Automatic WLM (lets Redshift manage slot allocation
  dynamically).

### For TABLE_LOCK

- Identify and optionally terminate the blocking PID.
- Schedule COPY operations outside peak query hours.
- Use staging tables + swap (ALTER TABLE RENAME) to minimize lock
  duration for data loads.

### For COPY_IAM_ROLE

```sql
-- Add s3:GetObject to the cluster's IAM role policy
-- Via CLI: aws iam put-role-policy --role-name <role> ...
COPY <table> FROM 's3://...'
  IAM_ROLE 'arn:aws:iam::<account>:role/<role-name>'
  ...
```

### For COPY_DATA_FORMAT

- Fix the DELIMITER, FORMAT, or ENCODING based on STL_LOAD_ERRORS.
- Use `FILLRECORD` / `FILLMISSING` for ragged data files.
- Use `ACCEPTINVCHARS` to replace invalid characters with `?`.
- Validate the data file encoding before COPY.

### For DIST_KEY_SKEW

```sql
-- Change distribution to KEY on the join column
ALTER TABLE <fact_table> ALTER DISTSTYLE KEY DISTKEY (<join_column>);

-- For small dimension tables, use ALL
ALTER TABLE <dim_table> ALTER DISTSTYLE ALL;

-- After changing, update statistics
ANALYZE <table>;
```

### For SORT_KEY_MISALIGNMENT

```sql
-- Add or change sort key
ALTER TABLE <table> ALTER SORTKEY (<filter_column>);

-- For multiple independent filter columns
ALTER TABLE <table> ALTER SORTKEY INTERLEAVED (<col1>, <col2>);

-- After changing, VACUUM to sort the data
VACUUM SORT ONLY <table>;
ANALYZE <table>;
```

### For NESTED_LOOP_JOIN

- Add the missing join condition.
- Fix data type mismatches on join columns (CAST or ALTER COLUMN
  TYPE).
- Avoid joining on UDF outputs.
- Use explicit JOIN syntax (not comma-separated FROM).

### For CONNECTION_LIMIT

- Implement connection pooling (pgbouncer, application-level pool).
- Reduce idle connection lifetime.
- Scale the cluster to a node type with more connection capacity.

### For SSL_TLS_ERROR

- Set `sslmode=require` (or `verify-ca`) in the client connection
  string.
- Ensure `require_ssl` in the parameter group matches the client
  capability.
- Download the latest Redshift CA certificate from AWS.

### For VACUUM_BLOCKED

- Schedule VACUUM during low-write windows.
- Use `VACUUM DELETE ONLY` for reclaiming deleted rows.
- Use `VACUUM SORT ONLY` for re-sorting unsorted rows.
- Consider a deep copy for severely fragmented tables.

### For ENCODING_CONVERSION

- `SET client_encoding TO 'UTF8';` for the session.
- Add `ENCODING AS UTF8` or `ENCODING AS LATIN1` to the COPY command.
- Clean mixed-encoding data before loading.

## Deep reference: Redshift query execution layer model

### Symptom -> layer decision matrix (offline classification)

```
Error string / EXPLAIN signal                     -> Layer
"cancelled due to queue timeout"                  -> WLM_QUEUE_TIMEOUT
Query hangs; STV_LOCKS shows granted=false         -> TABLE_LOCK
stl_load_errors                                    -> COPY_IAM_ROLE / COPY_DATA_FORMAT
DS_DIST_ALL_INNER / DS_BCAST_INNER in EXPLAIN      -> DIST_KEY_SKEW
Seq Scan on large table in EXPLAIN                 -> SORT_KEY_MISALIGNMENT
Nested Loop in EXPLAIN                             -> NESTED_LOOP_JOIN
"too many connections"                             -> CONNECTION_LIMIT
"SSL certificate verification failed"              -> SSL_TLS_ERROR
"character ... has no equivalent in encoding"      -> ENCODING_CONVERSION
VACUUM running for hours                           -> VACUUM_BLOCKED
```

### Distribution style decision guide

| Table profile | Recommended DISTSTYLE | Why |
|---|---|---|
| Large fact table (> 5M rows), joins on a specific column | KEY on the join column | Co-locates matching rows for DS_DIST_NONE joins |
| Small dimension table (< 2-5M rows) | ALL | Replicates to all nodes; all joins are local |
| Staging table (loaded and queried independently) | EVEN | Even distribution for parallel scan; no join co-location needed |
| Table with no joins (used standalone) | EVEN | Balanced parallel scan |

### Sort key decision guide

| Query pattern | Recommended sort key | Why |
|---|---|---|
| Range filter on a single date column | Compound (date_column) | Zone maps skip blocks outside the date range |
| Range filter on date + equality on dimension | Compound (date_column, dim_column) | Date is primary filter; dim is secondary |
| Equality filters on 2-3 independent columns | Interleaved (col1, col2, col3) | Equal-weight zone maps for any filter combination |
| No range filters, full scans only | (no sort key) | No zone map benefit; save sort maintenance cost |

### EXPLAIN scan type reference

| EXPLAIN signal | Meaning | Performance impact |
|---|---|---|
| `Seq Scan` | Full table scan, no sort key elimination | Slow on large tables |
| `Sort` | Sort key leveraged; zone maps skip blocks | Fast -- blocks eliminated |
| `DS_DIST_NONE` | Join is co-located; no redistribution | Optimal |
| `DS_DIST_ALL_INNER` | Inner table broadcast to all nodes | Costly on large tables |
| `DS_BCAST_INNER` | Inner table broadcast (same as ALL_INNER) | Costly |
| `DS_DIST_ALL_NONE` | Outer table broadcast; inner stays | OK for small outer tables |
| `XN Hash Join` | Hash-based join (normal) | Good |
| `XN Merge Join` | Merge-based join (requires sorted inputs) | Good if inputs are sorted |
| `XN Nested Loop` | Cartesian product | Almost always a bug |

### WLM queue types

| Queue (service_class) | Default purpose | Typical config |
|---|---|---|
| Queue 1-5 | System / maintenance | Managed by Redshift |
| Queue 6+ | User-defined | Configurable via WLM |
| Superuser queue | DBA operations | Accessed via `SET query_group TO 'superuser'` |

With Automatic WLM (default on newer clusters), Redshift dynamically
manages memory and concurrency. Manual WLM queues are defined in the
parameter group via `wlm_json_configuration`.

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

## Recent AWS features (2024-2026)

- **Automatic WLM (2024-2025):** Redshift dynamically manages query
  queue memory and concurrency. Manual WLM queue tuning is less
  critical on clusters with Auto WLM enabled, but queue timeout
  configuration still matters.
- **Redshift Serverless (2024-2025):** Workgroup-based, no cluster
  management. WLM concepts change to RPU (Redshift Processing Unit)
  scaling. Connection limits scale with base RPU capacity.
- **Late materialization for sort keys (2024):** Redshift defers
  fetching column data until after zone map filtering, improving scan
  performance on wide tables with selective sort keys.
- **AUTO DISTSTYLE and AUTO SORTKEY (2024-2025):** Redshift can
  automatically select distribution style and sort keys based on
  query patterns. Use `ALTER TABLE ... ALTER DISTSTYLE AUTO` to
  enable.
- **Data API enhancements (2024-2025):** The Redshift Data API now
  supports longer-running queries and better error messages, making
  it viable for programmatic diagnosis without a persistent JDBC
  connection.
- **Concurrency scaling (2024-2025):** Redshift automatically adds
  transient clusters to handle burst query workloads. WLM queue
  contention may be mitigated by concurrency scaling, but the root
  cause of queue saturation should still be addressed.

## Domain

AWS CloudOps / Amazon Redshift, Query Performance Diagnostics,
Distribution and Sort Key Design, Workload Management, and COPY
Data Ingestion.

## AWS documentation

- **Amazon Redshift Database Developer Guide -- Tuning query performance** -- https://docs.aws.amazon.com/redshift/latest/dg/c-optimizing-query-performance.html
- **Choosing distribution styles** -- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-best-distkey.html
- **Choosing sort keys** -- https://docs.aws.amazon.com/redshift/latest/dg/c_best-practices-sort-key.html
- **EXPLAIN** -- https://docs.aws.amazon.com/redshift/latest/dg/r_EXPLAIN.html
- **WLM query queues** -- https://docs.aws.amazon.com/redshift/latest/dg/cm-c-implementing-workload-management.html
- **COPY command** -- https://docs.aws.amazon.com/redshift/latest/dg/r_COPY.html
- **STL_LOAD_ERRORS** -- https://docs.aws.amazon.com/redshift/latest/dg/r_STL_LOAD_ERRORS.html
- **STV_LOCKS** -- https://docs.aws.amazon.com/redshift/latest/dg/r_STV_LOCKS.html
- **SVV_TABLE_INFO** -- https://docs.aws.amazon.com/redshift/latest/dg/r_SVV_TABLE_INFO.html
- **VACUUM** -- https://docs.aws.amazon.com/redshift/latest/dg/r_VACUUM_command.html
