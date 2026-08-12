---
name: athena-query-failure-troubleshooter
description: >-
  Diagnoses Amazon Athena query failures through a thirteen-category
  diagnostic tree: S3 bucket access denied (Glue Data Catalog vs S3
  data bucket permissions), SerDe mismatch (OpenCSVSerDe vs
  LazySimpleSerDe vs ParquetHiveSerDe), column type mismatch (STRING
  vs INT vs DOUBLE), partition projection errors, incorrect table
  location, stale Glue Catalog partitions (MSCK REPAIR), CTAS (CREATE
  TABLE AS) destination bucket permissions, workgroup output location,
  service query timeout (30-min limit), data format inference errors,
  SerDe property misconfiguration (quoteChar, escapeChar,
  separatorChar), ARRAY/STRUCT nested type issues, and date format
  parsing. Walks symptoms to a verified root cause with evidence-backed
  probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages, DDL, and query text. Live-account diagnosis uses aws athena get-query-execution, aws athena get-work-group, aws glue get-table, aws glue get-partitions, aws glue get-database, aws s3 ls / api head-bucket, aws cloudwatch get-metric-statistics on AWS/Athena, and aws logs get-query-results (AWS CLI v2, SSO or key-based credentials).
keywords:
- Athena
- SerDe
- OpenCSVSerDe
- LazySimpleSerDe
- ParquetHiveSerDe
- quoteChar
- separatorChar
- escapeChar
- column type mismatch
- STRING vs INT
- partition projection
- MSCK REPAIR
- stale partitions
- table location
- CTAS
- CREATE TABLE AS SELECT
- workgroup output location
- query timeout
- 30 minute timeout
- format inference
- nested type
- ARRAY
- STRUCT
- date parsing
- S3 access denied
- Glue Data Catalog
- troubleshooting
tags:
- athena
- analytics
- troubleshooting
- serde
- glue
- s3
- partition-projection
- ctas
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an Athena query failure (column returns NULL or wrong values, query returns zero rows unexpectedly, S3 access denied, serde parsing error, column type mismatch, partition projection stale partitions, CTAS destination permission denied, workgroup output location misconfigured, query exceeds 30-minute service timeout, format inference fails, nested ARRAY/STRUCT type error, or date parsing error), walking a symptom to the failed config layer with verify commands, validating why a "SELECT * FROM table LIMIT 10" returns garbled data or empty results, or triaging a "the Athena query broke" page where the root cause may be the SerDe, the Glue table definition, the partition metadata, the S3 permission, or the workgroup config — not necessarily the query SQL itself.
  when_not_to_use: Athena query performance optimization (use the athena-query-optimizer skill), Athena workgroup configuration posture audit (use the athena-workgroup-auditor skill), Glue crawler design or ETL pipeline debugging (use the glue-crawler-job-auditor or glue-job-troubleshooter skills), or Spark on Athena (Athena for Apache Spark) notebook debugging (use the Athena Spark documentation). This skill diagnoses query-time failures; it does not optimize slow-but-successful queries or audit workgroup security posture.
  activation_triggers:
  - Athena query failed
  - Athena COLUMN_NOT_FOUND
  - Athena column returns NULL
  - Athena zero rows
  - Athena access denied S3
  - Athena SerDe error
  - OpenCSVSerDe Athena
  - LazySimpleSerDe Athena
  - column type mismatch Athena
  - STRING vs INT Athena
  - partition projection Athena
  - MSCK REPAIR Athena
  - stale partitions Athena
  - CTAS Athena permission denied
  - CREATE TABLE AS SELECT Athena
  - workgroup output location Athena
  - Athena query timeout
  - Athena 30 minute limit
  - Athena format inference
  - nested type ARRAY STRUCT Athena
  - date parsing Athena
  - Athena SYNTAX_ERROR
  - troubleshoot Athena query
  invocation_schema: 'Input: either (a) a symptom description (error message from get-query-execution, observed behaviour "column returns NULL", "query returns zero rows", "CTAS failed with access denied"), optionally paired with the DDL (CREATE TABLE statement), the query text, and the workgroup name, OR (b) a QueryExecutionId plus region for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {S3_PERMISSION, GLUE_PERMISSION, SERDE_MISMATCH, COLUMN_TYPE_MISMATCH, PARTITION_PROJECTION, TABLE_LOCATION, STALE_PARTITIONS, CTAS_OUTPUT_LOCATION, WORKGROUP_OUTPUT, QUERY_TIMEOUT, FORMAT_INFERENCE, SERDE_PROPERTY, NESTED_TYPE_ERROR, DATE_PARSE_ERROR, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"Athena query on table orders_csv returns NULL for every\ncolumn except the first. The underlying S3 data is a CSV file with\ntab separators.\"\nDatabase: analytics\nTable: orders_csv\nQuery: SELECT * FROM analytics.orders_csv LIMIT 10\nDDL:\n  CREATE EXTERNAL TABLE orders_csv (\n    order_id STRING, customer_id STRING, amount STRING\n  )\n  ROW FORMAT SERDE\n    'org.apache.hadoop.hive.serde2.OpenCSVSerDe'\n  WITH SERDEPROPERTIES (\n    'separatorChar' = ','\n  )\n  STORED AS INPUTFORMAT\n    'org.apache.hadoop.mapred.TextInputFormat'\n  OUTPUTFORMAT\n    'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'\n  LOCATION 's3://prod-analytics/orders/'\nWorkgroup: primary\nQueryExecutionId: (offline — no live query)"
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

Four behaviours separate a senior Athena engineer from a generalist:

- **The SerDe choice determines the parsing rules for every row.**
  `OpenCSVSerDe` treats every column as STRING, respects
  `quoteChar` and `escapeChar`, and handles embedded commas inside
  quoted fields. `LazySimpleSerDe` is a delimited SerDe with
  `field.delim`, `line.delim`, and `collection.delim` — it does NOT
  handle quoted fields. `ParquetHiveSerDe` reads columnar Parquet
  files and ignores SerDe properties. Using `LazySimpleSerDe` for a
  CSV with quoted fields produces NULL on fields containing commas.
  Using `OpenCSVSerDe` for Parquet files fails entirely. The SerDe
  MUST match the file format on S3.

- **Partition projection replaces MSCK REPAIR permanently.** MSCK
  REPAIR TABLE enumerates S3 prefixes and creates Glue partition
  entries one by one — it is O(n) in the number of partitions and
  slow for tables with thousands of partitions. Partition projection
  configures the partition key range on the table itself (`projection.dt.type
  = date`, `projection.dt.range = '2024-01-01,2026-12-31'`,
  `projection.dt.format = 'yyyy-MM-dd'`), and Athena computes the
  partition list at query time without S3 listing. The fix for "new
  partitions not visible" is to configure partition projection, not to
  run MSCK REPAIR every day.

- **CTAS output goes to the workgroup result location, not the source
  table location.** When you run `CREATE TABLE new_table AS SELECT
  ...`, Athena writes the result data to the workgroup's configured
  output location (`s3://<result-bucket>/Unsaved-or-query-id/`), NOT
  to the `LOCATION` specified in the CTAS `WITH` clause if any. The
  new table's `LOCATION` in Glue is set to the actual output path
  AFTER the write. Permission failures on CTAS are almost always on
  the workgroup result bucket, not the table location bucket.

- **Athena has TWO permission layers: Glue Data Catalog and S3 data
  bucket.** The IAM principal running the query needs `glue:GetTable`,
  `glue:GetPartitions`, `glue:GetDatabase` on the catalog AND
  `s3:GetObject`, `s3:ListBucket` on the data bucket. A query that
  fails with "Insufficient permissions to execute the query ...
 .amazonaws.com is not authorized to perform: glue:GetTable" is a
  Glue permission issue. A query that fails with "QUERY_FAILED:
  Access Denied s3://bucket/path" is an S3 permission issue. The two
  are separate and must both pass.

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

```bash
# 1. Query execution details (state, error, bytes scanned, timing)
aws athena get-query-execution \
  --query-execution-id <id> --output json

# 2. Workgroup configuration (result location, enforcement, limits)
aws athena get-work-group \
  --work-group <name> --output json

# 3. Glue table definition (SerDe, columns, location, properties)
aws glue get-table \
  --database-name <db> --name <table> --output json

# 4. Glue partitions (check for stale / missing partition metadata)
aws glue get-partitions \
  --database-name <db> --table-name <table> --output json | \
  jq '.Partitions | length'

# 5. S3 data bucket verification (does the data exist and what format?)
aws s3 ls s3://<bucket>/<prefix>/ --recursive --summarize \
  --profile <p> | head -20

aws s3api head-object \
  --bucket <bucket> --key <key-of-a-data-file> --output json

# 6. CloudWatch: Athena query metrics (bytes scanned, query count)
aws cloudwatch get-metric-statistics --namespace AWS/Athena \
  --metric-name TotalExecutionTime \
  --dimensions Name=WorkGroup,Value=<wg> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

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

These are the operational gotchas a senior Athena engineer knows from
incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **OpenCSVSerDe treats ALL columns as STRING regardless of the DDL
  column type.** If the DDL declares `amount INT` but uses
  `OpenCSVSerDe`, the value is read as STRING internally and cast to
  INT. If the data contains "N/A" or empty strings in that column,
  the cast fails silently (returns NULL) or throws a
  `HIVE_CURSOR_ERROR`. Operators who "know the column is INT" miss
  that OpenCSVSerDe reads it as STRING first.

- **LazySimpleSerDe does NOT handle quoted CSV fields.** A CSV file
  with `"Smith, John",35,100.0` parsed by LazySimpleSerDe with
  `field.delim=','` produces 4 fields: `Smith`, ` John"`, `35`,
  `100.0`. The embedded comma splits the quoted name. Only
  OpenCSVSerDe handles quoted CSV fields correctly.

- **Athena engine version matters.** Athena engine v2 (2020) and v3
  (2022, Trino-based) have different function support, different
  error messages, and different type coercion rules. v3 is stricter
  on implicit casts; a query that worked on v2 may fail on v3 with
  `TYPE_MISMATCH`. Check the workgroup's
  `EngineVersion.SelectedEngineVersion` before debugging a "worked
  yesterday, broke today" failure.

- **Partition projection is configured on the TABLE, not the
  workgroup.** The projection properties (`projection.*`) are table
  properties in Glue. A workgroup change does not affect projection.
  Operators who "enabled partition projection on the workgroup" have
  not actually enabled it — it must be on the table's TBLPROPERTIES.

- **MSCK REPAIR TABLE does not scale beyond a few hundred
  partitions.** For a table with 10,000 partitions, MSCK REPAIR lists
  every S3 prefix and creates one partition entry per prefix — it can
  take hours and may time out. Partition projection or
  `ALTER TABLE ADD PARTITION` for specific ranges is the scalable
  alternative.

- **CTAS output location is determined by the workgroup, not the
  query.** Even if the CTAS has `WITH (external_location =
  's3://...')`, when `EnforceWorkGroupConfiguration: true`, Athena
  writes to the workgroup result location. The
  `external_location` is silently ignored. Operators who debug the
  `external_location` bucket permission while the output goes to the
  workgroup bucket debug the wrong bucket.

- **Parquet and ORC ignore SerDeProperties.** Columnar formats are
  self-describing; the SerDe reads the embedded schema. Setting
  `separatorChar` on a Parquet table is a no-op. Operators who "set
  SerDe properties" on a Parquet table and see no effect are
  configuring a format that does not use those properties.

- **Athena's `DATE` type is a calendar date (no time); `TIMESTAMP`
  has time but no zone.** Athena does not have a `TIMESTAMP WITH TIME
  ZONE` type. A Parquet file written with an instant timezone will
  appear shifted in Athena. Use `TIMESTAMP` for UTC instants; use
  `from_iso8601_timestamp()` for parsing.

- **`SELECT *` on a table with a wrong SerDe may SUCCEED but return
  NULL columns.** A query that returns no error but has NULL values
  in some columns is a SerDe mismatch, not a query failure. The
  query status is SUCCEEDED; the data is wrong. Always read actual
  row values, not just query status.

- **Glue Data Catalog permissions are on the catalog resource
  (account-level) and database/table (resource-level).** The IAM role
  needs `glue:GetTable`, `glue:GetPartitions`, `glue:GetDatabase`
  minimum. A Lake Formation-enabled catalog adds LF-Tags and
  database-level grants on top of IAM. Operators who "added the IAM
  policy" but still see Glue AccessDenied may have Lake Formation
  blocking at the LF-Tag level.

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

Symptom: query succeeds but columns return NULL or wrong values. OR
`HIVE_CURSOR_ERROR` on specific rows.

```bash
aws glue get-table \
  --database-name <db> --name <table> --output json | \
  jq '.Table.{StorageDescriptor: .StorageDescriptor.SerdeInfo, Columns: .StorageDescriptor.Columns}'
```

Check the SerDe info:

| SerDe | Handles | Does NOT handle |
|---|---|---|
| `OpenCSVSerDe` | CSV with quoted fields; configurable `separatorChar`, `quoteChar`, `escapeChar` | Non-STRING column types (reads as STRING, casts); custom delimiters other than separator/quote/escape |
| `LazySimpleSerDe` | Delimited text (tab, pipe, comma); configurable `field.delim`, `line.delim`, `collection.delim`, `mapkey.delim` | Quoted fields; CSV with embedded delimiters inside quotes |
| `ParquetHiveSerDe` | Parquet columnar | Text/CSV; ignores SerDeProperties |
| `OrcSerde` | ORC columnar | Text/CSV; ignores SerDeProperties |
| `JsonSerDe` (`org.openx.data.jsonserde.JsonSerDe`) | JSON (one JSON object per line) | Multi-line JSON; CSV |
| `AvroSerDe` | Avro | Text/CSV |

Common SerDe property errors:

| Property | Error | Fix |
|---|---|---|
| `separatorChar` set to `,` but data is tab-delimited | Fields not split correctly; NULL columns | Set `separatorChar = '\t'` or switch to LazySimpleSerDe with `field.delim = '\t'` |
| `quoteChar` set to `"` but data uses `'` | Quoted fields not stripped properly | Set `quoteChar = "'"` |
| `escapeChar` set to `\` but data uses `""` (CSV-style escaping) | Escaped quotes not parsed | Set `escapeChar = '"'` or use default OpenCSVSerDe (handles `""`) |
| OpenCSVSerDe with `serialization.null.format` not set | Empty strings returned as `""` instead of NULL | Set `serialization.null.format = ''` |

**Verdicts:**
- SerDe does not match file format (e.g., OpenCSVSerDe on Parquet):
  ROOT_CAUSE_IDENTIFIED, `LAYER: SERDE_MISMATCH`. Fix: change SerDe to
  ParquetHiveSerDe.
- SerDe is correct but SerDeProperties are wrong (e.g.,
  separatorChar mismatch): ROOT_CAUSE_IDENTIFIED,
  `LAYER: SERDE_PROPERTY`. Fix: update SerDeProperties.

#### To update the SerDe

```sql
-- Drop and recreate the table with the correct SerDe
-- (Athena does not support ALTER TABLE SET SERDEPROPERTIES directly)
DROP TABLE analytics.orders_csv;

CREATE EXTERNAL TABLE analytics.orders_csv (
  order_id STRING, customer_id STRING, amount STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerDe'
WITH SERDEPROPERTIES (
  'separatorChar' = '\t',
  'quoteChar' = '"',
  'escapeChar' = '\\'
)
STORED AS TEXTFILE
LOCATION 's3://prod-analytics/orders/';
```

### Step 3: Stale partitions and partition projection

Symptom: query returns zero rows on data that exists on S3. Partition
keys are non-null in the query predicate.

```bash
aws glue get-partitions \
  --database-name <db> --table-name <table> --output json | \
  jq '.Partitions | {count: length, values: [.[].Values]}'
```

If `count: 0` but S3 has partition directories, the partition metadata
is not loaded.

#### 3a: MSCK REPAIR (immediate fix, does not scale)

```sql
MSCK REPAIR TABLE analytics.orders_csv;
```

This loads partition metadata by listing S3 prefixes. For tables with
few partitions (< 100), this is the quickest fix. For large tables,
use `ALTER TABLE ADD PARTITION` for specific ranges.

#### 3b: Partition projection (permanent fix)

Configure partition projection on the table's TBLPROPERTIES:

```sql
-- For a table partitioned by dt (date) with daily partitions
ALTER TABLE analytics.orders_csv SET TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.dt.type' = 'date',
  'projection.dt.range' = '2024-01-01,2026-12-31',
  'projection.dt.format' = 'yyyy-MM-dd',
  'storage.location.template' = 's3://prod-analytics/orders/dt=${dt}'
);
```

Partition projection auto-loads partitions based on the pattern;
no MSCK REPAIR needed for new partitions.

| Projection property | Effect |
|---|---|
| `projection.enabled = true` | Enables partition projection for the table |
| `projection.<col>.type` | `enum`, `integer`, `date`, `injection` |
| `projection.<col>.range` | Valid range (for `integer` / `date`) |
| `projection.<col>.values` | Enumerated values (for `enum`) |
| `projection.<col>.format` | Date or integer format (e.g., `yyyy-MM-dd`) |
| `storage.location.template` | S3 path template with `${col}` substitution |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: STALE_PARTITIONS` (if MSCK
REPAIR fixes it) or `LAYER: PARTITION_PROJECTION` (if projection is
not configured and should be).

### Step 4: S3 and Glue permission

Symptom: `Access Denied s3://...` or `glue:GetTable is not authorized`.

#### 4a: S3 permission

```bash
# Check if the IAM role can list and get objects on the data bucket
aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names s3:GetObject s3:ListBucket \
  --resource-arns arn:aws:s3:::<bucket> arn:aws:s3:::<bucket>/* \
  --output json --profile <p>
```

The role needs:
- `s3:ListBucket` on `arn:aws:s3:::<bucket>`
- `s3:GetObject` on `arn:aws:s3:::<bucket>/*`

Also check the bucket policy (it can deny even when IAM allows):

```bash
aws s3api get-bucket-policy --bucket <bucket> --output json --profile <p>
```

If the role lacks S3 permissions, ROOT_CAUSE_IDENTIFIED,
`LAYER: S3_PERMISSION`.

#### 4b: Glue Data Catalog permission

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names glue:GetTable glue:GetPartitions glue:GetDatabase \
  --resource-arns arn:aws:glue:<region>:<acct>:catalog \
    arn:aws:glue:<region>:<acct>:database/<db> \
    arn:aws:glue:<region>:<acct>:table/<db>/<table> \
  --output json --profile <p>
```

If the role lacks Glue permissions, ROOT_CAUSE_IDENTIFIED,
`LAYER: GLUE_PERMISSION`.

If the catalog has Lake Formation enabled, also check LF-Tags:

```bash
aws lakeformation list-permissions \
  --principal DataLakePrincipalIdentifier=<role-arn> --output json
```

Lake Formation grants override IAM; an IAM allow does not help if Lake
Formation does not grant access.

### Step 5: CTAS output location

Symptom: `CREATE TABLE AS SELECT` fails with Access Denied.

```bash
aws athena get-work-group --work-group <wg> --output json | \
  jq '.WorkGroup.Configuration.ResultConfiguration.OutputLocation'

aws athena get-work-group --work-group <wg> --output json | \
  jq '.WorkGroup.Configuration.EnforceWorkGroupConfiguration'
```

The CTAS output goes to:
1. The workgroup result location (if
   `EnforceWorkGroupConfiguration: true`) — overrides everything.
2. The `external_location` in the CTAS (if
   `EnforceWorkGroupConfiguration: false`).
3. The client-side output location (if neither is set).

Check the IAM role's permission on the RESULT bucket:

```bash
aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names s3:PutObject s3:AbortMultipartUpload \
  --resource-arns arn:aws:s3:::<result-bucket>/* \
  --output json --profile <p>
```

The role needs `s3:PutObject` on the result bucket. If missing,
ROOT_CAUSE_IDENTIFIED, `LAYER: CTAS_OUTPUT_LOCATION`.

| CTAS failure pattern | Cause |
|---|---|
| Access Denied on workgroup result bucket | Role lacks `s3:PutObject` on the result bucket |
| CTAS writes to unexpected bucket | `EnforceWorkGroupConfiguration: true` overrides `external_location` |
| CTAS table's LOCATION is wrong in Glue | The table LOCATION is set to the actual output path after the write; it will be under the result bucket, not the source table bucket |
| CTAS fails with "Query output location is not set" | Workgroup has no result location configured AND no client-side location provided |

### Step 6: Query timeout

Symptom: query killed near 30 minutes. `EngineExecutionTimeInMillis`
approaches 1,800,000.

```bash
aws athena get-query-execution \
  --query-execution-id <id> --output json | \
  jq '.QueryExecution.Statistics.{EngineExecutionTimeInMillis, DataScannedInBytes}'
```

Athena's DML query timeout is 30 minutes (1,800,000 ms). There is no
per-query override beyond this. The fix is data reduction:

| Pattern | Fix |
|---|---|
| Query scans too many partitions | Add partition predicates (`WHERE dt BETWEEN '...' AND '...'`) |
| Query scans too many columns | Use columnar format (Parquet, ORC) to avoid full scans; `SELECT` only needed columns |
| Complex JOIN on large tables | Pre-aggregate with materialized views; use CTAS to pre-join |
| Non-partitioned table with full scan | Partition the table; convert to columnar format |
| Workgroup `BytesScannedCutoffPerQuery` exceeded | Raise the cutoff (if policy allows) or reduce scan via partitioning |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: QUERY_TIMEOUT`. Fix:
reduce data scanned (partition pruning, columnar format, materialized
views).

### Step 7: Format inference error

Symptom: `HIVE_BAD_DATA: Error parsing field value for field X` or
`Error opening Hive split s3://...`.

```bash
aws s3api head-object \
  --bucket <bucket> --key <data-file-key> --output json --profile <p>

# Download a sample to inspect the actual format
aws s3 cp s3://<bucket>/<key> /tmp/sample --profile <p>
head -5 /tmp/sample
```

Check the actual file format against the table's `STORED AS` and SerDe:

| Table `STORED AS` / SerDe | Actual file | Result |
|---|---|---|
| `TEXTFILE` + OpenCSVSerDe | Parquet file | `HIVE_BAD_DATA` — binary Parquet bytes parsed as text |
| `PARQUET` + ParquetHiveSerDe | CSV text | `HIVE_BAD_DATA` — text bytes parsed as Parquet |
| `ORC` + OrcSerde | JSON | `HIVE_BAD_DATA` |
| `TEXTFILE` + JsonSerDe | CSV | `HIVE_BAD_DATA` — CSV is not valid JSON |
| `INPUTFORMAT` mismatch | Any | Error reading the input format |

If the file format does not match, ROOT_CAUSE_IDENTIFIED,
`LAYER: FORMAT_INFERENCE` (or `LAYER: SERDE_MISMATCH` if the SerDe is
wrong but the format is consistent).

### Step 8: Nested type error (ARRAY / STRUCT)

Symptom: `cannot resolve field` on a nested column, or `SYNTAX_ERROR:
Expected column, but found array`.

```bash
aws glue get-table \
  --database-name <db> --name <table> --output json | \
  jq '.Table.StorageDescriptor.Columns[] | select(.Type | test("array|struct|map"))'
```

Common nested type issues:

| Issue | Cause | Fix |
|---|---|---|
| `col[0]` returns NULL on `ARRAY<STRING>` | Empty array or out-of-bounds index | Check array length with `cardinality(col)`; use `col[1]` (Athena arrays are 1-indexed in Trino v3) |
| `SELECT col.field` fails on `STRUCT<field: ...>` | Wrong field name or case | Use `col.field` (case-insensitive in v3) or `col["field"]`; verify field name in DDL |
| `UNNEST(col)` fails | `col` is not an array | Check the column type; wrap in `ARRAY[col]` if it is a scalar |
| Nested JSON column parsed as STRING | Table uses OpenCSVSerDe instead of JsonSerDe | Change SerDe to JsonSerDe for JSON data |
| `MAP<STRING,STRING>` field returns NULL | Map key does not exist | Use `element_at(col, 'key')` or `col['key']`; check `map_keys(col)` |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: NESTED_TYPE_ERROR`.

### Step 9: Date parse error

Symptom: date column returns NULL, or `INVALID_FORMAT` error, or date
is shifted by a day.

Check the DDL column type and the data format:

```bash
aws glue get-table \
  --database-name <db> --name <table> --output json | \
  jq '.Table.StorageDescriptor.Columns[] | select(.Type | test("date|timestamp"))'
```

| Issue | Cause | Fix |
|---|---|---|
| Column declared `DATE` but data has timestamp strings | Athena cannot parse "2024-01-15 10:30:00" as DATE | Change column type to `TIMESTAMP`; or use `date_trunc('day', parse_datetime(...))` |
| Column declared `TIMESTAMP` but data has epoch integers | Athena cannot parse epoch as TIMESTAMP | Use `from_unixtime(col)` in the query; or change column to `BIGINT` |
| Parquet column written with a timezone | Athena `TIMESTAMP` is zoneless; values appear shifted | Use `AT TIME ZONE 'UTC'` in the query; or re-write Parquet without timezone |
| `date_format(col, 'yyyy-MM-dd')` fails | Wrong function for Athena engine v3 | Use `format_datetime(col, 'yyyy-MM-dd')` (Trino syntax) |
| `from_iso8601_date(col)` fails | Column is already `DATE`, not STRING | `from_iso8601_date` expects STRING input; remove the function if column is already DATE |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: DATE_PARSE_ERROR`.

### Step 10: Column type mismatch

Symptom: column declared as INT but data contains "N/A" or empty
strings. `HIVE_CURSOR_ERROR` on specific rows.

```bash
# Download a sample to inspect actual values
aws s3 cp s3://<bucket>/<key> /tmp/sample --profile <p>
# Check for non-numeric values in the column
cut -d',' -f<col-index> /tmp/sample | sort | uniq -c | sort -rn | head
```

| Pattern | Cause | Fix |
|---|---|---|
| Column declared INT; data has "N/A", empty strings, or "null" | OpenCSVSerDe reads as STRING then casts; cast fails → NULL or error | Declare as STRING; use `TRY(CAST(col AS INT))` in queries; or clean the data |
| Column declared DOUBLE; data has "inf", "nan" | Parquet may handle; CSV SerDe does not | Use STRING + `TRY(CAST(...))`; or clean data |
| Column declared BOOLEAN; data has "1"/"0" or "yes"/"no" | Athena BOOLEAN expects "true"/"false" | Use STRING + conditional cast |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: COLUMN_TYPE_MISMATCH`.

### Step 11: Table location wrong

Symptom: `COLUMN_NOT_FOUND`, or query on a table returns data from the
wrong S3 prefix.

```bash
aws glue get-table \
  --database-name <db> --name <table> --output json | \
  jq '.Table.StorageDescriptor.Location'
```

Check the `LOCATION`:

| Issue | Cause | Fix |
|---|---|---|
| `LOCATION` points to `s3://bucket/path/` (with trailing slash) but data is at `s3://bucket/path` | Athena reads from the exact prefix; trailing slash may double up | Match the trailing slash to the S3 key prefix |
| `LOCATION` points to a different bucket or prefix than where the data lives | Wrong table definition; data moved | Update `LOCATION` via `ALTER TABLE SET LOCATION 's3://...'` |
| `LOCATION` points to the bucket root (`s3://bucket/`) | Athena scans all objects in the bucket; may pick up unrelated files | Set `LOCATION` to the specific prefix (`s3://bucket/data/orders/`) |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: TABLE_LOCATION`.

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

```text
TARGET: analytics.events_daily / QueryExecutionId: (offline)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Query returns zero rows for dt='2026-08-05' even though S3
  has s3://prod-analytics/events/dt=2026-08-05/. glue get-partitions
  returns count=0; the partition metadata was never loaded for the
  new date. The table has no partition projection configured, so new
  partitions require MSCK REPAIR (Step 3).
LAYER: STALE_PARTITIONS
EVIDENCE:
  - Symptom: SELECT count(*) FROM analytics.events_daily WHERE
    dt='2026-08-05' returns 0; data exists on S3.
  - Probe: aws glue get-partitions returns count=0.
  - Probe: aws s3 ls s3://prod-analytics/events/dt=2026-08-05/
    returns data files.
  - Passing: SerDe correct (ParquetHiveSerDe on Parquet files);
    permissions verified; table LOCATION correct
    (s3://prod-analytics/events/).
REMEDIATION:
  1. Immediate fix: MSCK REPAIR TABLE analytics.events_daily; (loads
     the missing partition metadata).
  2. Permanent fix: configure partition projection so future dates
     auto-load:
     ALTER TABLE analytics.events_daily SET TBLPROPERTIES (
       'projection.enabled' = 'true',
       'projection.dt.type' = 'date',
       'projection.dt.range' = '2024-01-01,2026-12-31',
       'projection.dt.format' = 'yyyy-MM-dd',
       'storage.location.template' =
         's3://prod-analytics/events/dt=${dt}'
     );
  3. Verify: SELECT count(*) FROM analytics.events_daily WHERE
     dt='2026-08-05' should return > 0.
CONFIRM: Before running MSCK REPAIR or ALTER TABLE, emit and await
  operator approval.
```

### Worked example — CTAS output location permission

```text
TARGET: analytics.orders_summary_ctas / QueryExecutionId: (offline)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: CTAS failed with Access Denied on
  s3://aws-athena-query-results-111111111111-us-east-1/tables/....
  The workgroup (primary) has EnforceWorkGroupConfiguration=true with
  OutputLocation pointing at aws-athena-query-results-.... The IAM
  role lacks s3:PutObject on that result bucket. The operator's
  CTAS external_location clause was silently overridden by the
  enforced workgroup config (Step 5).
LAYER: CTAS_OUTPUT_LOCATION
EVIDENCE:
  - Symptom: CREATE TABLE orders_summary AS SELECT ... failed with
    "Access Denied s3://aws-athena-query-results-...".
  - Probe: aws athena get-work-group returns
    EnforceWorkGroupConfiguration=true,
    OutputLocation=s3://aws-athena-query-results-111111111111-us-east-1.
  - Probe: aws iam simulate-principal-policy on the role for
    s3:PutObject on arn:aws:s3:::aws-athena-query-results-111111111111-us-east-1/*
    returns implicitDeny.
  - Passing: Glue permissions verified; source table S3 permissions
    verified; query SQL is valid.
REMEDIATION:
  1. Add s3:PutObject on the workgroup result bucket to the IAM role:
     {
       "Effect": "Allow",
       "Action": ["s3:PutObject",
                  "s3:AbortMultipartUpload"],
       "Resource": "arn:aws:s3:::aws-athena-query-results-111111111111-us-east-1/*"
     }
  2. Verify: re-run the CTAS; it should complete and the new table
     LOCATION should be under the result bucket.
CONFIRM: Before updating the IAM policy, emit and await operator
  approval.
```

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

- **MANDATORY CONFIRMATION GATE.** Before any state-changing SQL
  (`DROP TABLE`, `CREATE TABLE`, `ALTER TABLE`, `MSCK REPAIR`,
  `CREATE TABLE AS SELECT`), emit and await operator approval.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`get-query-execution`, `get-work-group`, `glue get-table`,
  `glue get-partitions`, `s3 ls`, `s3api head-object`,
  `iam simulate-principal-policy`). Do not perform state-changing
  operations as diagnostic probes.

- **DROP TABLE** removes the Glue table definition but does NOT delete
  S3 data. It is recoverable (recreate the table with the same DDL).
  However, it invalidates any downstream queries referencing the table.

- **ALTER TABLE SET LOCATION** changes where Athena reads data from.
  Pointing it at the wrong prefix returns wrong or empty results.
  Always verify the S3 path before applying.

- **ALTER TABLE SET TBLPROPERTIES** for partition projection is safe
  and non-destructive. It changes how Athena resolves partitions; it
  does not move data. Verify with a test query after applying.

- **CREATE TABLE AS SELECT** writes data to S3. It consumes storage
  and incurs scan charges. Verify the `external_location` (or
  workgroup result location) has sufficient capacity and the right
  permissions before running.

- **MSCK REPAIR TABLE** lists S3 prefixes and creates Glue partition
  entries. For large tables it can be slow and may time out. Test on
  a small partition range first.

- **IAM policy changes** affect every principal using the role. Tighten
  policies gradually; verify with `simulate-principal-policy` before
  and after.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple tables (e.g., a wrong SerDe across
  a set of CSV tables), batch remediation into groups of at most 5
  tables, emit a single CONFIRM per batch, and verify between batches.

## Remediation guidance

### For SERDE_MISMATCH

Drop and recreate the table with the correct SerDe for the file
format:

| File format | Correct SerDe |
|---|---|
| CSV with quoted fields | `OpenCSVSerDe` |
| CSV without quoted fields | `LazySimpleSerDe` or `OpenCSVSerDe` |
| Tab/pipe delimited | `LazySimpleSerDe` with `field.delim` |
| Parquet | `ParquetHiveSerDe` |
| ORC | `OrcSerde` |
| JSON (one object per line) | `org.openx.data.jsonserde.JsonSerDe` |
| Avro | `AvroSerDe` |

### For SERDE_PROPERTY

Update the SerDeProperties to match the data:

```sql
-- Recreate the table with corrected SerDeProperties
CREATE EXTERNAL TABLE <table> (...)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerDe'
WITH SERDEPROPERTIES (
  'separatorChar' = '\t',
  'quoteChar' = '"',
  'escapeChar' = '\\'
)
STORED AS TEXTFILE
LOCATION 's3://...';
```

### For STALE_PARTITIONS

```sql
-- Immediate: load missing partition metadata
MSCK REPAIR TABLE <db>.<table>;
```

### For PARTITION_PROJECTION

```sql
ALTER TABLE <db>.<table> SET TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.<col>.type' = 'date',
  'projection.<col>.range' = '2024-01-01,2026-12-31',
  'projection.<col>.format' = 'yyyy-MM-dd',
  'storage.location.template' = 's3://<bucket>/<prefix>/<col>=${<col>}'
);
```

### For S3_PERMISSION

Add the minimum-scope S3 permissions to the IAM role:

```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:GetObjectVersion"],
  "Resource": "arn:aws:s3:::<data-bucket>/*"
},
{
  "Effect": "Allow",
  "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
  "Resource": "arn:aws:s3:::<data-bucket>"
}
```

### For GLUE_PERMISSION

Add Glue Data Catalog permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "glue:GetDatabase", "glue:GetDatabases",
    "glue:GetTable", "glue:GetTables",
    "glue:GetPartition", "glue:GetPartitions"
  ],
  "Resource": [
    "arn:aws:glue:<region>:<acct>:catalog",
    "arn:aws:glue:<region>:<acct>:database/<db>",
    "arn:aws:glue:<region>:<acct>:table/<db>/<table>"
  ]
}
```

If Lake Formation is enabled, grant LF-Tags or database-level access:

```bash
aws lakeformation grant-permissions \
  --principal DataLakePrincipalIdentifier=<role-arn> \
  --permissions SELECT DESCRIBE \
  --resource '{ "Table": {"DatabaseName": "<db>", "Name": "<table>"}}'
```

### For CTAS_OUTPUT_LOCATION

Add `s3:PutObject` and `s3:AbortMultipartUpload` on the workgroup
result bucket to the IAM role. Verify with
`simulate-principal-policy`.

### For QUERY_TIMEOUT

- Add partition predicates to prune scan range.
- Convert to columnar format (Parquet, ORC) to reduce bytes scanned.
- Use materialized views for repeated complex aggregations.
- Pre-join large tables via CTAS.
- Raise workgroup `BytesScannedCutoffPerQuery` if the limit (not the
  30-min timeout) is the cause.

### For FORMAT_INFERENCE

Fix the table's `STORED AS` and SerDe to match the actual file format.
Download a sample file and inspect it before recreating the table.

### For NESTED_TYPE_ERROR

- Fix the DDL to declare the correct `ARRAY<...>`, `STRUCT<...>`, or
  `MAP<...>` type.
- Use the correct accessor (`col[1]` for arrays, `col.field` for
  structs, `col['key']` for maps).
- Use `UNNEST(col)` to flatten arrays in queries.
- Use JsonSerDe for JSON data with nested fields.

### For DATE_PARSE_ERROR

- Fix the DDL column type (`DATE` vs `TIMESTAMP` vs `STRING`).
- Use Trino date functions (`format_datetime`, `from_iso8601_date`,
  `date_add`, `date_diff`).
- For epoch columns, use `from_unixtime(col)` and declare as `BIGINT`.

### For COLUMN_TYPE_MISMATCH

- Declare the column as STRING and use `TRY(CAST(col AS INT))` in
  queries for safe casting.
- Or clean the source data to remove non-numeric values.

### For TABLE_LOCATION

```sql
ALTER TABLE <db>.<table> SET LOCATION 's3://<correct-bucket>/<prefix>/';
```

Verify the path with `aws s3 ls` before applying.

## Deep reference: Athena failure layer model

### SerDe matrix

| SerDe class | Format | Handles quoted fields | Column types | Key properties |
|---|---|---|---|---|
| `OpenCSVSerDe` | CSV/Text | Yes (`quoteChar`, `escapeChar`) | ALL columns read as STRING | `separatorChar`, `quoteChar`, `escapeChar` |
| `LazySimpleSerDe` | Delimited Text | No | Native (INT, STRING, etc.) | `field.delim`, `line.delim`, `collection.delim`, `mapkey.delim` |
| `ParquetHiveSerDe` | Parquet | n/a | Native (from Parquet schema) | (ignored) |
| `OrcSerde` | ORC | n/a | Native (from ORC schema) | (ignored) |
| `JsonSerDe` (openx) | JSON (one object per line) | n/a | Native | `ignore.malformed.json` |
| `AvroSerDe` | Avro | n/a | Native (from Avro schema) | `avro.schema.literal` or `avro.schema.url` |

### Workgroup configuration matrix

| Config | Effect |
|---|---|
| `ResultConfiguration.OutputLocation` | Where query results and CTAS output go |
| `EnforceWorkGroupConfiguration` | `true` = overrides client-side output location; `false` = client can override |
| `BytesScannedCutoffPerQuery` | Query fails if bytes scanned exceeds this; 0 = no limit (use sparingly) |
| `RequesterPaysEnabled` | Allows queries on RequesterPays S3 buckets |
| `EngineVersion.SelectedEngineVersion` | `Athena engine 2` or `Athena engine 3` (Trino); affects function support and type coercion |
| `PublishCloudWatchMetricsEnabled` | Whether query metrics are emitted to CloudWatch |

### Athena error category matrix

| Error category | Meaning | Layer |
|---|---|---|
| `SYNTAX_ERROR` | SQL syntax or function mismatch | Re-examine query; check engine version |
| `HIVE_BAD_DATA` | File format does not match table SerDe | SERDE_MISMATCH / FORMAT_INFERENCE |
| `HIVE_CURSOR_ERROR` | Row-level parsing error (bad value for column type) | SERDE_MISMATCH / COLUMN_TYPE_MISMATCH |
| `COLUMN_NOT_FOUND` | Column in query does not exist in table definition | Check DDL; stale table definition |
| `Access Denied` (S3) | IAM role lacks S3 permissions on data or result bucket | S3_PERMISSION / CTAS_OUTPUT_LOCATION |
| `is not authorized to perform: glue:*` | IAM role lacks Glue Data Catalog permissions | GLUE_PERMISSION |
| `Query exhausted resources` | 30-minute timeout hit | QUERY_TIMEOUT |
| `INSUFFICIENT_RESOURCES` | Workgroup per-query byte limit exceeded | Raise BytesScannedCutoffPerQuery or reduce scan |
| `TABLE_NOT_FOUND` | Table does not exist in Glue catalog | Check database/table name; cross-account catalog |
| `PARTITION_NOT_FOUND` | Partition metadata not loaded | STALE_PARTITIONS / PARTITION_PROJECTION |

### Partition projection properties reference

| Property | Purpose |
|---|---|
| `projection.enabled` | Master switch (`true` / `false`) |
| `projection.<col>.type` | `enum`, `integer`, `date`, `injection` |
| `projection.<col>.range` | For `integer` / `date`: start,end |
| `projection.<col>.values` | For `enum`: comma-separated list |
| `projection.<col>.interval` | For `integer` / `date`: step (default 1) |
| `projection.<col>.interval.unit` | For `date`: `DAYS`, `HOURS`, `MINUTES` |
| `projection.<col>.format` | For `date`: format pattern (`yyyy-MM-dd`); for `integer`: padding |
| `projection.<col>.digits` | For `integer`: zero-padding width |
| `storage.location.template` | S3 path with `${col}` substitution |

### Athena engine v2 vs v3 differences

| Feature | v2 (Presto) | v3 (Trino) |
|---|---|---|
| Date format function | `date_format(col, '%Y-%m-%d')` | `format_datetime(col, 'yyyy-MM-dd')` |
| Date parse function | `date_format(col, '%Y-%m-%d')` | `from_iso8601_date(col)`, `date_parse` |
| Array indexing | 1-indexed | 1-indexed (unchanged) |
| Type coercion | More permissive implicit casts | Stricter; may reject implicit casts that v2 allowed |
| GEOMETRY | Supported | Different function names |
| Error messages | Presto-style | Trino-style |

## Recent AWS features (2024-2026)

- **Athena engine version 3 (Trino) default (2024):** All new
  workgroups default to engine v3 (Trino). Existing workgroups on v2
  can be upgraded. Diagnostically, v3 is stricter on type coercion;
  queries that relied on v2 implicit casts may fail with
  `TYPE_MISMATCH` or `SYNTAX_ERROR`.
- **Partition projection GA (2024):** Partition projection is the
  recommended replacement for MSCK REPAIR on all partitioned tables.
  Diagnostically, tables without projection require MSCK REPAIR or
  ALTER TABLE ADD PARTITION for every new partition; tables with
  projection auto-load.
- **Athena notebook sessions (2024-2025):** Athena for Apache Spark
  supports notebook sessions. This is a separate compute model from
  the SQL engine; this skill covers SQL engine failures, not Spark
  notebook failures.
- **Athena parameterized queries (2024-2025):** Athena supports
  parameterized queries (execStatement with parameters). Diagnostically,
  parameter binding errors (`INVALID_PARAMETER`) are distinct from
  SQL syntax errors.
- **Multi-catalog support (2024-2025):** Athena can query external
  Hive metastores and Lambda-based federated catalogs. Diagnostically,
  a `TABLE_NOT_FOUND` on a federated catalog may be a Lambda function
  failure, not a Glue issue.
- **Athena query result reuse (2024-2025):** Athena can cache and
  reuse query results for identical queries. Diagnostically, a query
  that returns stale results may be hitting the result cache; check
  `ResultReuseByAgeConfiguration` on the workgroup.

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
