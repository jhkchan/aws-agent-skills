# Error Handling (load on demand) — Athena Query Failure Troubleshooter

Error category matrix and per-layer remediation guidance moved verbatim from SKILL.md. Loaded on demand.

---

## Remediation guidance (moved from SKILL.md)

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

---

## Athena error category matrix (moved from SKILL.md)

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
