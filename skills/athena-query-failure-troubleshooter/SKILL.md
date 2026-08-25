---
name: athena-query-failure-troubleshooter
description: 'Diagnoses Amazon Athena query failures through a thirteen-category diagnostic tree: S3 bucket access denied (Glue Data Catalog vs S3 data bucket permissions), SerDe mismatch (OpenCSVSerDe vs LazySimpleSerDe vs ParquetHiveSerDe), column type mismatch (STRING vs INT vs DOUBLE), partition projection errors, incorrect table location, stale Glue Catalog partitions (MSCK REPAIR), CTAS (CREATE TABLE AS) destination bucket permissions, workgroup output location, service query timeout (30-min limit), data format inference errors, SerDe property misconfiguration (quoteChar, escapeChar, separatorChar), ARRAY/STRUCT nested type issues, and date format parsing. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages, DDL, and query text. Live-account diagnosis uses aws athena get-query-execution, aws athena get-work-group, aws glue get-table, aws glue get-partitions, aws glue get-database, aws s3 ls / api head-bucket, aws cloudwatch get-metric-statistics on AWS/Athena, and aws logs get-query-results (AWS CLI v2, SSO or key-based credentials).
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
  when_to_use: Diagnosing an Athena query failure (column returns NULL or wrong values, query returns zero rows unexpectedly, S3 access denied, serde parsing error, column type mismatch, partition projection stale partitions, CTAS destination permission denied, workgroup output location misconfigured, query exceeds 30-minute service timeout, format inference fails, nested ARRAY/STRUCT type error, or date parsing error), walking a symptom to the failed config layer with verify commands, validating why a "SELECT * FROM table LIMIT 10" returns garbled data or empty results, or triaging a "the Athena query broke" page where the root cause may be the SerDe, the Glue table definition, the partition metadata, the S3 permission, or the workgroup config — not necessarily the query SQL itself.
  when_not_to_use: Athena query performance optimization (use the athena-query-optimizer skill), Athena workgroup configuration posture audit (use the athena-workgroup-auditor skill), Glue crawler design or ETL pipeline debugging (use the glue-crawler-job-auditor or glue-job-troubleshooter skills), or Spark on Athena (Athena for Apache Spark) notebook debugging (use the Athena Spark documentation). This skill diagnoses query-time failures; it does not optimize slow-but-successful queries or audit workgroup security posture.
  activation_triggers: Athena query failed, Athena COLUMN_NOT_FOUND, Athena column returns NULL, Athena zero rows, Athena access denied S3, Athena SerDe error, OpenCSVSerDe Athena, LazySimpleSerDe Athena, column type mismatch Athena, STRING vs INT Athena, partition projection Athena, MSCK REPAIR Athena, stale partitions Athena, CTAS Athena permission denied, CREATE TABLE AS SELECT Athena, workgroup output location Athena, Athena query timeout, Athena 30 minute limit, Athena format inference, nested type ARRAY STRUCT Athena, date parsing Athena, Athena SYNTAX_ERROR, troubleshoot Athena query
  invocation_schema: 'Input: either (a) a symptom description (error message from get-query-execution, observed behaviour "column returns NULL", "query returns zero rows", "CTAS failed with access denied"), optionally paired with the DDL (CREATE TABLE statement), the query text, and the workgroup name, OR (b) a QueryExecutionId plus region for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {S3_PERMISSION, GLUE_PERMISSION, SERDE_MISMATCH, COLUMN_TYPE_MISMATCH, PARTITION_PROJECTION, TABLE_LOCATION, STALE_PARTITIONS, CTAS_OUTPUT_LOCATION, WORKGROUP_OUTPUT, QUERY_TIMEOUT, FORMAT_INFERENCE, SERDE_PROPERTY, NESTED_TYPE_ERROR, DATE_PARSE_ERROR, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"Athena query on table orders_csv returns NULL for every\ncolumn except the first. The underlying S3 data is a CSV file with\ntab separators.\"\nDatabase: analytics\nTable: orders_csv\nQuery: SELECT * FROM analytics.orders_csv LIMIT 10\nDDL:\n  CREATE EXTERNAL TABLE orders_csv (\n    order_id STRING, customer_id STRING, amount STRING\n  )\n  ROW FORMAT SERDE\n    'org.apache.hadoop.hive.serde2.OpenCSVSerDe'\n  WITH SERDEPROPERTIES (\n    'separatorChar' = ','\n  )\n  STORED AS INPUTFORMAT\n    'org.apache.hadoop.mapred.TextInputFormat'\n  OUTPUTFORMAT\n    'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'\n  LOCATION 's3://prod-analytics/orders/'\nWorkgroup: primary\nQueryExecutionId: (offline — no live query)"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Athena, SerDe, OpenCSVSerDe, LazySimpleSerDe, ParquetHiveSerDe, quoteChar, separatorChar, escapeChar, column type mismatch, STRING vs INT, partition projection, MSCK REPAIR, stale partitions, table location, CTAS, CREATE TABLE AS SELECT, workgroup output location, query timeout, 30 minute timeout, format inference, nested type, ARRAY, STRUCT, date parsing, S3 access denied, Glue Data Catalog, troubleshooting
  tags: athena, analytics, troubleshooting, serde, glue, s3, partition-projection, ctas
---

# Athena Query Failure Troubleshooter

## Quick start

- **The SerDe determines the parsing rules (memorise this).** Athena
  reads the table's `ROW FORMAT SERDE` to know how to parse each row.
  An `OpenCSVSerDe` with `separatorChar=','` expects comma-delimited
  fields; a `LazySimpleSerDe` with `'field.delim'='\t'` expects
  tab-delimited. A mismatch between the SerDe properties and the
  actual file format produces NULL columns, truncated rows, or
  SYNTAX_ERROR — not a runtime crash. The #1 Athena failure a senior
  data engineer sees is a SerDe that does not match the data.
- **Symptom → layer map (first plausible match drives the first
  probe):** columns return NULL or wrong values → SERDE_MISMATCH /
  SERDE_PROPERTY; query returns zero rows on data that exists →
  STALE_PARTITIONS / PARTITION_PROJECTION; "Access Denied s3://..." →
  S3_PERMISSION; CTAS fails with permission error →
  CTAS_OUTPUT_LOCATION; query killed at 30 minutes → QUERY_TIMEOUT;
  nested ARRAY/STRUCT error → NESTED_TYPE_ERROR; date column returns
  NULL or wrong date → DATE_PARSE_ERROR; "COLUMN_NOT_FOUND" →
  COLUMN_TYPE_MISMATCH or stale table definition.
- **Partition projection replaces MSCK REPAIR.** `MSCK REPAIR TABLE`
  loads partition metadata by listing S3 prefixes — slow, expensive,
  and needs re-running after every new partition. Partition projection
  auto-loads partitions based on a naming pattern configured on the
  table. Operators who run `MSCK REPAIR` on every new day's data are
  paying for a workaround that partition projection solves permanently.
- **CTAS output goes to the workgroup result location, NOT the source
  table location.** A `CREATE TABLE AS SELECT` writes the result to
  `s3://<workgroup-result-bucket>/tables/<query-id>/`. The new table's
  `LOCATION` points there. Operators who think CTAS writes to the
  source table's S3 bucket debug the wrong permission.
- **A 30-minute timeout is a hard service limit.** Athena kills any
  query exceeding 30 minutes (DML) or 600 DDL hour limit. There is no
  per-query timeout override for DML beyond 30 minutes. A query that
  scans a large partition range with a complex JOIN will hit this
  limit; the fix is data reduction (partition pruning, columnar
  format, materialized views), not a timeout increase.

## Mindset

An Athena query failure is almost always a metadata or permission
incident wearing a SQL costume. The SQL is usually fine; the broken
thing is the SerDe choice, the Glue table definition, the partition
metadata, the S3 bucket policy, the workgroup output location, or the
data format inference. Treat the query text as innocent until the
SerDe, the table definition, the partition metadata, the IAM
permissions on both Glue and S3, and the workgroup config are each
proven correct. Senior data engineers start with
`get-query-execution` (for the exact error), then `glue get-table`
(for the DDL and SerDe), then `s3 ls` (for the data format) — and only
re-examine the SQL after all three are confirmed.

## Philosophy

Senior-engineer philosophy moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the reasoning behind SerDe choice, partition projection, CTAS output, and the two permission layers.

## Quick reference — symptom triage table

| Symptom / error message | Most likely layer | First probe |
|---|---|---|
| Columns return NULL or truncated; data exists on S3 | SERDE_MISMATCH / SERDE_PROPERTY | `glue get-table` → check SerDe + SerDeProperties vs actual file format |
| Query returns zero rows on data that exists; partition keys non-null | STALE_PARTITIONS / PARTITION_PROJECTION | `glue get-partitions`; check if partition metadata exists; MSCK REPAIR or projection config |
| `Access Denied s3://bucket/path` | S3_PERMISSION | IAM role's S3 permissions on data bucket |
| `glue:GetTable ... is not authorized` | GLUE_PERMISSION | IAM role's Glue permissions on catalog/database |
| CTAS fails with Access Denied | CTAS_OUTPUT_LOCATION | Workgroup result location bucket; IAM `s3:PutObject` on result bucket |
| Query killed at ~30 minutes | QUERY_TIMEOUT | `EngineExecutionTimeInMillis` ≈ 1800000; data scan volume |
| `mismatched input`, `extraneous input`, `cannot resolve` | SYNTAX_ERROR (SQL) | Re-examine query text; check function support in Athena engine |
| `COLUMN_NOT_FOUND` or `cannot resolve column` | TABLE_LOCATION / stale table | `glue get-table` → check columns vs actual query |
| `HIVE_BAD_DATA`, `HIVE_CURSOR_ERROR`, parsing exception | SERDE_MISMATCH / FORMAT_INFERENCE | `s3 head-object`; check actual file format vs table's `STORED AS` |
| ARRAY/STRUCT field error; `SYNTAX_ERROR: Column type is array` | NESTED_TYPE_ERROR | DDL column definition; nested SerDe (json) for array/struct |
| Date column returns NULL; `INVALID_FORMAT` | DATE_PARSE_ERROR | DDL column type (DATE vs STRING); `date_format` / `from_iso8601_date` usage |
| Column declared INT but data has "N/A" or empty string | COLUMN_TYPE_MISMATCH | DDL column type vs actual data values |
| None of the above; insufficient DDL or error detail | INSUFFICIENT_DATA | Ask for QueryExecutionId, DDL, sample row |

## Pre-flight: query state and gather-info gate

Before running symptom-specific probes, gather the query execution
details and short-circuit on query states that mimic failures.

### Account-wide pre-flight commands

Account-wide pre-flight command listing moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand for live-account diagnosis before running symptom-specific probes.

### Query-state short-circuit

| `Status` from get-query-execution | Effect on diagnosis |
|---|---|
| `SUCCEEDED` | Query completed. If the symptom is wrong data (NULL columns, zero rows), the query ran but the SerDe or table definition is wrong. Route to SERDE_MISMATCH or STALE_PARTITIONS. |
| `FAILED` | Query failed. Read `StateChangeReason` for the error category. Route to the matching branch below. |
| `CANCELLED` | Query was cancelled (user or service). If cancelled by the service near 30 minutes, route to QUERY_TIMEOUT. |
| `QUEUED` / `RUNNING` | Query is still in flight; wait for completion before diagnosing. |
| `FAILED` with `HIVE_BAD_DATA` | Data format on S3 does not match the table's SerDe or `STORED AS` format. Route to SERDE_MISMATCH / FORMAT_INFERENCE. |
| `FAILED` with `Access Denied` or `is not authorized` | Permission issue. Route to S3_PERMISSION or GLUE_PERMISSION based on the denied resource. |
| `FAILED` with `Query exhausted resources at <X> milliseconds` | QUERY_TIMEOUT (30-min service limit hit). |

### Workgroup-state short-circuit

| Workgroup config | Effect |
|---|---|
| `EnforceWorkGroupConfiguration: true` + result location set | All query output goes to the workgroup result location, overriding any client-side output location. CTAS output goes here. |
| `EnforceWorkGroupConfiguration: false` | Client-side output location can override the workgroup default. CTAS may write to a client-specified location. |
| `BytesScannedCutoffPerQuery` set | Query fails if it scans more than N bytes. A "resource exhausted" error may be this limit, not the 30-minute timeout. |
| `RequesterPaysEnabled: true` | Queries on buckets in other accounts with RequesterPays require the IAM role to accept charges. |

If the input is malformed (missing QueryExecutionId or missing DDL +
error message for offline classification), emit INSUFFICIENT_DATA.

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on
the observed error or behaviour, then walk the layer-specific probes
in order. Each layer ends with either a positive root-cause
confirmation (failing probe that matches the symptom) or a pass that
moves to the next layer. **Never emit ROOT_CAUSE_IDENTIFIED without a
failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

Step 0 non-obvious behaviours moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when the obvious layer does not match the symptom.

### Step 1: Symptom entry — pick the diagnostic branch

| Symptom / error | Branch |
|---|---|
| Columns return NULL or wrong values; query succeeds | Step 2 — SerDe mismatch / property |
| Query returns zero rows; data exists on S3 | Step 3 — Stale partitions / partition projection |
| `Access Denied s3://...` or `glue:GetTable is not authorized` | Step 4 — S3 or Glue permission |
| CTAS fails with permission error | Step 5 — CTAS output location |
| Query killed near 30 minutes or `exhausted resources` | Step 6 — Query timeout |
| `HIVE_BAD_DATA` or format inference error | Step 7 — Format inference |
| ARRAY/STRUCT field error or nested type issue | Step 8 — Nested type |
| Date column returns NULL or wrong date | Step 9 — Date parse error |
| Column declared numeric but data has strings ("N/A", "") | Step 10 — Column type mismatch |
| Table location wrong; `COLUMN_NOT_FOUND` | Step 11 — Table location |
| None of the above | Step 12 — INSUFFICIENT_DATA |

### Step 2: SerDe mismatch and SerDe property error

Probes, SerDe capability table, SerDe-property error table, and the DROP/CREATE fix moved verbatim to [references/serde-and-partition-reference.md](references/serde-and-partition-reference.md).
Verdict: ROOT_CAUSE_IDENTIFIED with LAYER: SERDE_MISMATCH (wrong SerDe for the file format) or SERDE_PROPERTY (wrong SerDeProperties).

### Step 3: Stale partitions and partition projection

get-partitions probe, MSCK REPAIR, and partition-projection TBLPROPERTIES moved verbatim to [references/serde-and-partition-reference.md](references/serde-and-partition-reference.md).
Verdict: ROOT_CAUSE_IDENTIFIED with LAYER: STALE_PARTITIONS (MSCK REPAIR fixes it) or PARTITION_PROJECTION (not configured, should be).

### Step 4: S3 and Glue permission

simulate-principal-policy probes (S3, Glue, Lake Formation) moved verbatim to [references/permission-and-ctas-reference.md](references/permission-and-ctas-reference.md).
Verdict: ROOT_CAUSE_IDENTIFIED with LAYER: S3_PERMISSION or GLUE_PERMISSION — both layers must pass.

### Step 5: CTAS output location

Workgroup output-location probes and CTAS failure-pattern table moved verbatim to [references/permission-and-ctas-reference.md](references/permission-and-ctas-reference.md).
Verdict: ROOT_CAUSE_IDENTIFIED with LAYER: CTAS_OUTPUT_LOCATION — check the RESULT bucket, not the source bucket.

### Step 6: Query timeout

EngineExecutionTime probe and data-reduction fix table moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Verdict: ROOT_CAUSE_IDENTIFIED with LAYER: QUERY_TIMEOUT — 30 minutes is a hard limit; the fix is data reduction.

### Step 7: Format inference error

head-object probe and format-mismatch table moved verbatim to [references/serde-and-partition-reference.md](references/serde-and-partition-reference.md).
Verdict: ROOT_CAUSE_IDENTIFIED with LAYER: FORMAT_INFERENCE or SERDE_MISMATCH.

### Step 8: Nested type error (ARRAY / STRUCT)

Nested-column probe and ARRAY/STRUCT/MAP issue table moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Verdict: ROOT_CAUSE_IDENTIFIED with LAYER: NESTED_TYPE_ERROR.

### Step 9: Date parse error

Date-column probe and DATE/TIMESTAMP issue table moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Verdict: ROOT_CAUSE_IDENTIFIED with LAYER: DATE_PARSE_ERROR.

### Step 10: Column type mismatch

Sample-data probe and type-mismatch pattern table moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Verdict: ROOT_CAUSE_IDENTIFIED with LAYER: COLUMN_TYPE_MISMATCH.

### Step 11: Table location wrong

LOCATION probe and table-location issue table moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Verdict: ROOT_CAUSE_IDENTIFIED with LAYER: TABLE_LOCATION.

### Step 12: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, OR the input
lacks the QueryExecutionId (for live diagnosis), the DDL, or the error
message, emit INSUFFICIENT_DATA with the specific gaps. A
ROOT_CAUSE_IDENTIFIED verdict requires a failing probe that matches
the symptom; without the data to run the probe, the skill cannot
conclude.

## Output format

```text
TARGET: <database.table / query-execution-id>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <S3_PERMISSION | GLUE_PERMISSION | SERDE_MISMATCH |
        COLUMN_TYPE_MISMATCH | PARTITION_PROJECTION | TABLE_LOCATION |
        STALE_PARTITIONS | CTAS_OUTPUT_LOCATION | WORKGROUP_OUTPUT |
        QUERY_TIMEOUT | FORMAT_INFERENCE | SERDE_PROPERTY |
        NESTED_TYPE_ERROR | DATE_PARSE_ERROR | UNKNOWN>
EVIDENCE:
  - <observed symptom — error message or wrong-data behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with SQL or CLI command>
  2. <verification query after the fix>
CONFIRM: Before executing any state-changing SQL or CLI, emit and
  await operator approval.
```

### Worked example — SerDe mismatch, CSV with tab delimiter

```text
TARGET: analytics.orders_csv / QueryExecutionId: (offline)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Table orders_csv uses OpenCSVSerDe with separatorChar=','
  but the S3 data is tab-delimited CSV. OpenCSVSerDe splits on commas;
  a row like "ORD001\tCUST123\t150.00" is treated as a single field,
  producing NULL for columns 2 and 3. The SerDe separatorChar does
  not match the actual delimiter (Step 2).
LAYER: SERDE_PROPERTY
EVIDENCE:
  - Symptom: SELECT * FROM analytics.orders_csv LIMIT 10 returns
    order_id = "ORD001\tCUST123\t150.00" (entire row in column 1),
    customer_id = NULL, amount = NULL for every row.
  - Probe: aws glue get-table returns SerDeInfo.SerializationLibrary
    = org.apache.hadoop.hive.serde2.OpenCSVSerDe;
    SerdeInfo.Parameters.separatorChar = ",".
  - Probe: aws s3 cp s3://prod-analytics/orders/data.csv /tmp/ &&
    head -1 /tmp/data.csv returns "ORD001\tCUST123\t150.00" (tab-
    delimited, not comma).
  - Passing: Glue permissions verified (glue:GetTable allowed);
    S3 permissions verified (s3:GetObject allowed); partitions loaded
    (get-partitions returns count > 0); table LOCATION correct.
REMEDIATION:
  1. Recreate the table with the correct separatorChar:
     DROP TABLE analytics.orders_csv;
     CREATE EXTERNAL TABLE analytics.orders_csv (
       order_id STRING, customer_id STRING, amount STRING
     )
     ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerDe'
     WITH SERDEPROPERTIES ('separatorChar' = '\t')
     STORED AS TEXTFILE
     LOCATION 's3://prod-analytics/orders/';
  2. Verify: SELECT * FROM analytics.orders_csv LIMIT 10 should
     return order_id, customer_id, amount in separate columns with
     correct values.
CONFIRM: Before dropping and recreating the table, emit and await:
  "CONFIRM: About to DROP and RECREATE analytics.orders_csv with
   separatorChar='\t'. This does not affect S3 data. Proceed? (yes/no)"
```

### Worked example — Stale partitions, partition projection fix

Secondary worked example moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when emitting a STALE_PARTITIONS verdict.

### Worked example — CTAS output location permission

Secondary worked example moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when emitting a CTAS_OUTPUT_LOCATION verdict.

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is on a different layer.

- NEVER use LazySimpleSerDe for CSV data with quoted fields. Only
  OpenCSVSerDe handles embedded delimiters inside quoted fields.
  LazySimpleSerDe splits naively on `field.delim`, corrupting quoted
  values.

- NEVER assume OpenCSVSerDe column types are respected. OpenCSVSerDe
  reads ALL columns as STRING and casts at query time. A column
  declared INT with "N/A" values will return NULL or throw
  HIVE_CURSOR_ERROR. Use STRING + TRY(CAST(...)) for safe casts.

- NEVER rely on MSCK REPAIR TABLE for tables with more than a few
  hundred partitions. It is O(n) in partition count and slow.
  Configure partition projection instead.

- NEVER assume the CTAS output goes to the source table location.
  CTAS writes to the workgroup result location (when enforced) or the
  `external_location`. The new table's LOCATION is set to the actual
  output path AFTER the write. Permission failures on CTAS are on the
  result bucket, not the source bucket.

- NEVER assume a SUCCEEDED query means the data is correct. A SerDe
  mismatch produces a SUCCEEDED status with NULL columns. Always read
  actual row values, not just the query status.

- NEVER set SerDeProperties on a Parquet or ORC table and expect them
  to take effect. Columnar formats are self-describing; SerDeProperties
  (separatorChar, escapeChar, etc.) are ignored. Setting them is a
  no-op, not a configuration.

- NEVER use Athena engine v2 functions on a v3 workgroup without
  checking. v3 (Trino-based) uses Trino function names
  (`format_datetime`, `from_iso8601_timestamp`); v2 uses Presto names.
  A "worked yesterday, broke today" failure after a workgroup engine
  upgrade is often a function name change.

- NEVER diagnose a permission failure without checking BOTH Glue and
  S3. The IAM role needs glue:GetTable AND s3:GetObject. Adding only
  one produces a different AccessDenied on the other layer.

- NEVER ignore Lake Formation on a Glue Data Catalog. If Lake
  Formation is enabled, LF-Tag grants override IAM. An IAM allow does
  not help if Lake Formation does not grant access. Check
  `aws lakeformation list-permissions` alongside IAM.

- NEVER treat a 30-minute timeout as a configurable limit. Athena's
  DML query timeout is 30 minutes; there is no per-query override.
  The fix is data reduction (partitioning, columnar format), not a
  timeout increase.

- NEVER use `SELECT *` on a table with a suspected SerDe issue as
  your only diagnostic query. `SELECT *` may return NULL columns
  without error. Always also run `SELECT specific_column FROM table
  LIMIT 10` to see if individual column access reveals the parsing
  issue.

- NEVER assume Athena arrays are 0-indexed. Athena engine v3 (Trino)
  uses 1-indexed arrays: `col[1]` is the first element. Using `col[0]`
  returns NULL. Operators coming from Python/Java routinely make this
  error.

- NEVER set a workgroup's result location to a bucket the IAM role
  cannot write to. The result location must have `s3:PutObject`
  permission for every principal that runs queries in the workgroup.

## Pre-flight safety checks (run before any state-changing SQL)

Pre-flight safety checks (CONFIRMATION GATE, read-only-first rule, per-operation risk notes) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Keep here: every diagnostic probe is read-only; load the reference before any state-changing SQL.

## Remediation guidance

Per-layer remediation guidance (SQL, IAM policies, LF grants) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when writing the REMEDIATION block of the output.

## Deep reference: Athena failure layer model

### SerDe matrix

SerDe matrix moved verbatim to [references/serde-and-partition-reference.md](references/serde-and-partition-reference.md).
Load on demand when matching a SerDe class to a file format.

### Workgroup configuration matrix

Workgroup configuration matrix moved verbatim to [references/permission-and-ctas-reference.md](references/permission-and-ctas-reference.md).
Load on demand when the workgroup config changes the diagnosis.

### Athena error category matrix

Athena error category matrix moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when mapping an error string to a LAYER.

### Partition projection properties reference

Partition projection properties reference moved verbatim to [references/serde-and-partition-reference.md](references/serde-and-partition-reference.md).
Load on demand when configuring projection TBLPROPERTIES.

### Athena engine v2 vs v3 differences

Athena engine v2 vs v3 differences moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand on 'worked yesterday, broke today' engine-version failures.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when result reuse, parameterized queries, or federated catalogs are in play.

## References (load on demand)

- [references/serde-and-partition-reference.md](references/serde-and-partition-reference.md) — SerDe deep dive and partition projection reference; now also holds Steps 2, 3, 7 (probes and verdict tables), the SerDe matrix, and the projection properties table moved from SKILL.md.
- [references/permission-and-ctas-reference.md](references/permission-and-ctas-reference.md) — Glue/S3 permission and CTAS output location reference; now also holds Steps 4, 5 and the workgroup configuration matrix moved from SKILL.md.
- [references/worked-examples.md](references/worked-examples.md) — worked diagnostic examples moved from SKILL.md: Steps 6, 8, 9, 10, 11 layer deep dives plus the full stale-partitions and CTAS output examples.
- [references/error-handling.md](references/error-handling.md) — Athena error category matrix and per-layer remediation guidance moved from SKILL.md.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — account-wide pre-flight command listing and pre-flight safety checks moved from SKILL.md.
- [references/advanced-patterns.md](references/advanced-patterns.md) — senior-engineer philosophy, Step 0 non-obvious behaviours, engine v2 vs v3 differences, and recent AWS features moved from SKILL.md.

## Domain

AWS CloudOps / Amazon Athena (Interactive Query Service), Glue Data
Catalog Integration, S3 Data Lake, SerDe Parsing, Partition Strategy,
Workgroup Configuration.

## AWS documentation

- **Amazon Athena User Guide** — https://docs.aws.amazon.com/athena/latest/ug/what-is.html
- **Athena SerDe reference** — https://docs.aws.amazon.com/athena/latest/ug/serde-reference.html
- **OpenCSVSerDe** — https://docs.aws.amazon.com/athena/latest/ug/csv-serde.html
- **LazySimpleSerDe** — https://docs.aws.amazon.com/athena/latest/ug/lazy-simple-serde.html
- **Athena partition projection** — https://docs.aws.amazon.com/athena/latest/ug/partition-projection.html
- **Athena CTAS** — https://docs.aws.amazon.com/athena/latest/ug/ctas.html
- **Athena workgroups** — https://docs.aws.amazon.com/athena/latest/ug/workgroups-create-update-query.html
- **Athena engine version 3** — https://docs.aws.amazon.com/athena/latest/ug/engine-versions-reference-0003.html
- **Athena error messages** — https://docs.aws.amazon.com/athena/latest/ug/error-messages.html
- **Lake Formation with Athena** — https://docs.aws.amazon.com/athena/latest/ug/security-athena-lake-formation.html
- **Athena service quotas** — https://docs.aws.amazon.com/athena/latest/ug/service-limits.html
