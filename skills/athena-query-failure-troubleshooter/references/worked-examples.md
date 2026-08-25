# Worked Examples (load on demand) — Athena Query Failure Troubleshooter

Layer deep dives (Steps 6, 8-11) and full worked-example outputs moved verbatim from SKILL.md; the primary SerDe-mismatch example stays in SKILL.md. Loaded on demand.

---

## Step 6: Query timeout (moved from SKILL.md)

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

---

## Step 8: Nested type error (ARRAY / STRUCT) (moved from SKILL.md)

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

---

## Step 9: Date parse error (moved from SKILL.md)

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

---

## Step 10: Column type mismatch (moved from SKILL.md)

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

---

## Step 11: Table location wrong (moved from SKILL.md)

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

---

## Worked example — Stale partitions, partition projection fix (moved from SKILL.md)

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

---

## Worked example — CTAS output location permission (moved from SKILL.md)

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
