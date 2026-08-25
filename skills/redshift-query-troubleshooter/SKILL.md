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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Philosophy — four behaviours".
> Load when: reading EXPLAIN scan types, choosing DISTSTYLE, designing sort keys, or diagnosing queue hopping.
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

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) § "Account-wide pre-flight commands".
> Load when: gathering cluster state before symptom-specific probes (stl_query, stl_wlm_query, stv_locks, svv_table_info, stl_load_errors).
### Query-state short-circuit

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) § "Query-state short-circuit".
> Load when: classifying aborted/endtime/elapsed states before picking a branch.
If the input is malformed (missing cluster identifier, absent query
text or error message, no table context), emit:

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "INSUFFICIENT_DATA (malformed input)".
> Load when: the input is malformed — missing symptom, cluster id, query text, or table context.
## Process -- Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on
the observed symptom, then walk the layer-specific probes in order.
**Never emit ROOT_CAUSE_IDENTIFIED without a failing probe that
matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 0: Non-obvious behaviours".
> Load when: before trusting the obvious branch — dist key co-location, DISTSTYLE ALL cost, compound vs interleaved sort keys, queue-wait timeouts, COPY IAM/manifest subtleties, STL_LOAD_ERRORS granularity, vacuum locking, nested loops, connection limits, client encoding.
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

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) + [references/error-handling.md](references/error-handling.md) § "Step 2 — WLM queue timeout".
> Load when: running the stl_wlm_query / stv_wlm_service_class_config probes and interpreting queue vs execution time (fix list in references/error-handling.md).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: WLM_QUEUE_TIMEOUT`. Fix:

### Step 3: Table lock detection

Symptom: query hangs indefinitely, never completes or fails.

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) + [references/error-handling.md](references/error-handling.md) § "Step 3 — table lock".
> Load when: running the stv_locks + stv_inflight probes (lock patterns and fixes in references/error-handling.md).

A lock with `granted = false` means the PID is waiting for a lock held
by `lock_owner_pid` (which has `granted = true`).

> **Moved verbatim** → [references/error-handling.md](references/error-handling.md) § "Step 3 — lock patterns".
> Load when: matching a lock pattern to its cause (SELECT vs COPY, deadlock, VACUUM FULL).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TABLE_LOCK`. Fix:
> **Moved verbatim** → [references/error-handling.md](references/error-handling.md) § "Step 3 — TABLE_LOCK fixes".
> Load when: fixing TABLE_LOCK — terminate blocking PID, batch COPYs, schedule VACUUM.

### Step 4: COPY command failures

Symptom: `COPY` command fails with a load error or access denied.

#### 4a: Check STL_LOAD_ERRORS

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) + [references/error-handling.md](references/error-handling.md) § "Step 4 — COPY failures".
> Load when: probing COPY failures — STL_LOAD_ERRORS detail, IAM role verification, format error table, and manifest checks (fix tables in references/error-handling.md).

#### 4b: IAM role / S3 access



**ROOT_CAUSE_IDENTIFIED** with `LAYER: COPY_IAM_ROLE`. Fix: add
`s3:GetObject` on the bucket to the cluster's IAM role, or use
CREDENTIALS with explicit AWS access keys (not recommended).

#### 4c: Data format mismatch


**ROOT_CAUSE_IDENTIFIED** with `LAYER: COPY_DATA_FORMAT`. Fix: correct
the COPY parameters (DELIMITER, ENCODING, FORMAT, FILLRECORD) based on
the `stl_load_errors` detail.

#### 4d: S3 manifest mismatch

If using `COPY FROM 's3://bucket/manifest.json' manifest`:



### Step 5: Distribution key skew

Symptom: query is slow. EXPLAIN shows `DS_DIST_ALL_INNER` or
`DS_BCAST_INNER` (broadcast of the inner table).

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) + [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 5 — dist key skew".
> Load when: probing distribution styles and per-slice skew (pattern table in references/advanced-patterns.md).


**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DIST_KEY_SKEW`. Fix:
- Change the distribution style to KEY on the join column for both
  tables (`ALTER TABLE ... ALTER DISTSTYLE KEY (...)`).
- For small dimension tables (< 2-5M rows), use `DISTSTYLE ALL`.
- After changing, run ANALYZE to update table statistics.

### Step 6: Sort key misalignment

Symptom: query is slow. EXPLAIN shows `Seq Scan` on a large table
that should be using a range-restricted scan.

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) + [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 6 — sort key misalignment".
> Load when: probing sortkey1 and pg_table_def (effect table in references/advanced-patterns.md).


**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SORT_KEY_MISALIGNMENT`.
Fix: add or change the sort key to match the query's primary filter
column. For queries filtering on multiple independent columns,
consider an interleaved sort key (max 3-4 columns).


### Step 7: Nested loop join

Symptom: query is very slow. EXPLAIN shows `XN Nested Loop`.

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) + [references/advanced-patterns.md](references/advanced-patterns.md) + [references/error-handling.md](references/error-handling.md) § "Step 7 — nested loop join".
> Load when: confirming XN Nested Loop (meaning in references/advanced-patterns.md, cause table in references/error-handling.md).



**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: NESTED_LOOP_JOIN`. Fix:
add the missing join condition, fix the data type mismatch, or
redesign the query to avoid the Cartesian product.

### Step 8: Connection limit

Symptom: `FATAL: too many connections for "<database>"` or
`FATAL: remaining connection slots are reserved for non-replication
superuser connections`.

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) + [references/advanced-patterns.md](references/advanced-patterns.md) + [references/error-handling.md](references/error-handling.md) § "Step 8 — connection limit".
> Load when: counting stv_sessions (limit model in references/advanced-patterns.md, pattern fixes in references/error-handling.md).



**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CONNECTION_LIMIT`. Fix:
implement connection pooling, reduce idle connections, or scale the
cluster to a larger node type with more connection capacity.

### Step 9: SSL/TLS certificate issues

Symptom: `SSL certificate verification failed` or
`FATAL: no pg_hba.conf entry for host ... SSL off`.

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) + [references/error-handling.md](references/error-handling.md) § "Step 9 — SSL/TLS".
> Load when: checking require_ssl via parameter group (issue table in references/error-handling.md).


**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SSL_TLS_ERROR`. Fix: align
the client SSL settings with the cluster's `require_ssl` parameter.

### Step 10: Vacuum blocked

Symptom: `VACUUM` command runs for a very long time without completing.

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) + [references/error-handling.md](references/error-handling.md) § "Step 10 — vacuum blocked".
> Load when: checking svv_vacuum_progress, unsorted %, and write locks (issue table in references/error-handling.md).


**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: VACUUM_BLOCKED`. Fix:
schedule VACUUM during low-write windows, use VACUUM DELETE ONLY or
SORT ONLY, or perform a deep copy (create a new table with the right
sort key and INSERT INTO).

### Step 11: Encoding conversion

Symptom: `ERROR: character with byte sequence 0xXX in encoding "UTF8"
has no equivalent in encoding "LATIN1"` or similar.

> **Moved verbatim** → [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) + [references/error-handling.md](references/error-handling.md) § "Step 11 — encoding conversion".
> Load when: checking server/client encoding (fix table in references/error-handling.md).


**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ENCODING_CONVERSION`.

### Step 12: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, emit:

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Step 12 — INSUFFICIENT_DATA template".
> Load when: no branch produced a positive root-cause match.
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

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Worked example — WLM queue timeout".
> Load when: emitting a ROOT_CAUSE_IDENTIFIED block for a WLM_QUEUE_TIMEOUT diagnosis.
### Worked example -- COPY data format error

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Worked example — COPY data format error".
> Load when: emitting a ROOT_CAUSE_IDENTIFIED block for a COPY_DATA_FORMAT diagnosis.
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

> **Moved verbatim** → [references/error-handling.md](references/error-handling.md) § "Remediation guidance per layer".
> Load when: the root cause is identified — per-layer fix procedures for all eleven layers.
## Deep reference: Redshift query execution layer model

> **Moved verbatim** → [references/explain-scan-reference.md](references/explain-scan-reference.md) § "Symptom→layer matrix and decision guides".
> Load when: classifying offline by error string/EXPLAIN signal, or choosing DISTSTYLE / sort key by table and query profile.




## Recent AWS features (2024-2026)

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Recent AWS features (2024-2026)".
> Load when: diagnosing on Auto WLM, Serverless, late materialization, AUTO DISTSTYLE/SORTKEY, Data API, or concurrency-scaling clusters.
## References (load on demand)

- [references/diagnostic-sql-reference.md](references/diagnostic-sql-reference.md) — per-layer diagnostic SQL/CLI; now also holds the account-wide pre-flight block, the query-state short-circuit, every per-step probe, and the system-table quick reference moved from SKILL.md
- [references/explain-scan-reference.md](references/explain-scan-reference.md) — EXPLAIN scan types and decision guides; now also holds the symptom→layer matrix, distribution/sort decision guides, and WLM queue types moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples (WLM queue timeout, COPY format error), the Step 12 INSUFFICIENT_DATA template, and the malformed-input output
- [references/error-handling.md](references/error-handling.md) — per-step error/pattern tables, per-layer remediation guidance moved from SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — philosophy, Step 0 non-obvious behaviours, distribution/sort pattern tables, recent AWS features

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
