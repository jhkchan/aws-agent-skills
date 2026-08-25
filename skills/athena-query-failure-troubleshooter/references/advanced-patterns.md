# Advanced Patterns (load on demand) — Athena Query Failure Troubleshooter

Expert-knowledge deep dives, engine-version differences, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Philosophy — four behaviours of a senior Athena engineer (moved from SKILL.md)

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

---

## Step 0: Non-obvious behaviours that change diagnosis (moved from SKILL.md)

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

---

## Athena engine v2 vs v3 differences (moved from SKILL.md)

| Feature | v2 (Presto) | v3 (Trino) |
|---|---|---|
| Date format function | `date_format(col, '%Y-%m-%d')` | `format_datetime(col, 'yyyy-MM-dd')` |
| Date parse function | `date_format(col, '%Y-%m-%d')` | `from_iso8601_date(col)`, `date_parse` |
| Array indexing | 1-indexed | 1-indexed (unchanged) |
| Type coercion | More permissive implicit casts | Stricter; may reject implicit casts that v2 allowed |
| GEOMETRY | Supported | Different function names |
| Error messages | Presto-style | Trino-style |

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

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
