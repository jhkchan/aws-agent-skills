# Athena SerDe and Partition Projection Reference Guide

Supplementary reference for the Athena Query Failure Troubleshooter
skill. Loaded on-demand when a diagnostic needs SerDe specifics,
partition projection configuration, or workgroup output location rules.

## SerDe matrix — which SerDe for which format

| File format | Correct SerDe class | Handles quoted fields | Column types | Key SerDeProperties |
|---|---|---|---|---|
| CSV (with quoted fields) | `org.apache.hadoop.hive.serde2.OpenCSVSerDe` | Yes (`quoteChar`, `escapeChar`) | ALL columns read as STRING (cast at query time) | `separatorChar`, `quoteChar`, `escapeChar` |
| CSV (no quotes) or delimited | `org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe` | No | Native (INT, STRING, etc.) | `field.delim`, `line.delim`, `collection.delim`, `mapkey.delim` |
| Parquet | `org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe` | n/a | Native (from embedded Parquet schema) | (ignored) |
| ORC | `org.apache.hadoop.hive.ql.io.orc.OrcSerde` | n/a | Native (from embedded ORC schema) | (ignored) |
| JSON (one object per line) | `org.openx.data.jsonserde.JsonSerDe` | n/a | Native | `ignore.malformed.json` |
| JSON (alternative) | `com.amazon.ionhiveserde.IonHiveSerDe` | n/a | Native | Ion format specific |
| Avro | `org.apache.hadoop.hive.serde2.avro.AvroSerDe` | n/a | Native (from Avro schema) | `avro.schema.literal` or `avro.schema.url` |
| Regex / custom log | `org.apache.hadoop.hive.serde2.RegexSerDe` | n/a | Native | `input.regex` |

## OpenCSVSerDe — detailed behavior

OpenCSVSerDe is the most common source of Athena "NULL columns"
failures because of its non-obvious behavior:

1. **ALL columns are read as STRING** regardless of the DDL column
   type. If the DDL declares `amount INT`, OpenCSVSerDe reads the raw
   bytes as STRING and Athena casts to INT at query time.
2. **CAST("N/A" AS INT) returns NULL** in Athena engine v3 (Trino).
   In v2 (Presto), it may throw `INVALID_CAST_ARGUMENT`.
3. **`quoteChar` defaults to `"` (double-quote)**. If the CSV uses
   single-quotes, set `quoteChar = "'"`.
4. **`escapeChar` defaults to `\` (backslash)**. If the CSV uses CSV-
   style escaping (`""` for an embedded quote), set `escapeChar = '"'`
   or rely on the default OpenCSVSerDe behavior (handles `""` when
   `escapeChar` is not set).
5. **`separatorChar` defaults to `,` (comma)**. For tab-delimited,
   set `separatorChar = '\t'`. For pipe-delimited, `separatorChar = '|'`.

### OpenCSVSerDe property reference

| Property | Default | Valid values | Effect |
|---|---|---|---|
| `separatorChar` | `,` | Any single character | Field delimiter |
| `quoteChar` | `"` | Any single character | Quote character (wraps fields containing the separator) |
| `escapeChar` | `"` | Any single character | Escape character (escapes the quoteChar within a quoted field) |
| `serialization.null.format` | (not set) | String | Value to treat as NULL (e.g., `""` for empty strings as NULL) |

## LazySimpleSerDe — detailed behavior

LazySimpleSerDe is a native-type delimited SerDe:

1. **Respects DDL column types** (INT, BIGINT, DOUBLE, etc.). No
   internal STRING-to-native cast.
2. **Does NOT handle quoted fields**. A CSV row `"Smith, John",35`
   parsed with `field.delim=','` produces 3 fields: `Smith`, ` John"`,
   `35`. The embedded comma splits the quoted name.
3. **Configurable delimiters** via SerDeProperties.

### LazySimpleSerDe property reference

| Property | Default | Effect |
|---|---|---|
| `field.delim` | `\001` (Ctrl-A) | Field delimiter |
| `line.delim` | `\n` | Line delimiter |
| `collection.delim` | `\002` (Ctrl-B) | Collection element delimiter (for ARRAY columns) |
| `mapkey.delim` | `\003` (Ctrl-C) | Map key-value delimiter (for MAP columns) |
| `serialization.format` | same as `field.delim` | Alias for field.delim |

## Parquet and ORC — key behavior

- Columnar formats are **self-describing**: the file embeds the schema.
  The SerDe reads the embedded schema; SerDeProperties are ignored.
- **SerDeProperties (separatorChar, etc.) have no effect** on Parquet
  or ORC tables. Setting them is a no-op, not an error.
- The DDL column types **must match the Parquet/ORC schema**. A
  mismatch (e.g., DDL says INT but Parquet has BIGINT) produces
  `HIVE_BAD_DATA` or NULL columns.
- `STORED AS PARQUET` automatically selects ParquetHiveSerDe.
- `STORED AS ORC` automatically selects OrcSerde.

## Partition projection — complete property reference

### Enabling partition projection

```sql
ALTER TABLE <db>.<table> SET TBLPROPERTIES (
  'projection.enabled' = 'true'
);
```

### Partition column properties

| Property | Purpose | Required |
|---|---|---|
| `projection.<col>.type` | `enum`, `integer`, `date`, `injection` | Yes |
| `projection.<col>.range` | For `integer`/`date`: `start,end` | For `integer`/`date` |
| `projection.<col>.values` | For `enum`: comma-separated list | For `enum` |
| `projection.<col>.interval` | For `integer`/`date`: step value | No (default 1) |
| `projection.<col>.interval.unit` | For `date`: `DAYS`, `HOURS`, `MINUTES` | For `date` with interval |
| `projection.<col>.format` | For `date`: format pattern (`yyyy-MM-dd`); for `integer`: padding | For `date` |
| `projection.<col>.digits` | For `integer`: zero-padding width | No |

### Storage location template

| Property | Purpose |
|---|---|
| `storage.location.template` | S3 path with `${col}` substitution, e.g., `s3://bucket/path/dt=${dt}` |

### Common partition projection patterns

**Daily date partitions (Hive-style):**
```sql
'projection.enabled' = 'true',
'projection.dt.type' = 'date',
'projection.dt.range' = '2024-01-01,2026-12-31',
'projection.dt.format' = 'yyyy-MM-dd',
'storage.location.template' = 's3://bucket/events/dt=${dt}'
```

**Hourly date partitions:**
```sql
'projection.enabled' = 'true',
'projection.dt.type' = 'date',
'projection.dt.range' = '2024-01-01-00,2026-12-31-23',
'projection.dt.format' = 'yyyy-MM-dd-HH',
'projection.dt.interval.unit' = 'HOURS',
'storage.location.template' = 's3://bucket/events/dt=${dt}'
```

**Enum partitions (e.g., region):**
```sql
'projection.enabled' = 'true',
'projection.region.type' = 'enum',
'projection.region.values' = 'us-east-1,us-west-2,eu-west-1',
'storage.location.template' = 's3://bucket/events/region=${region}'
```

**Integer partitions (e.g., batch_id):**
```sql
'projection.enabled' = 'true',
'projection.batch.type' = 'integer',
'projection.batch.range' = '1,1000',
'projection.batch.digits' = '4',
'storage.location.template' = 's3://bucket/events/batch=${batch}'
```

### Partition projection vs MSCK REPAIR

| Dimension | MSCK REPAIR TABLE | Partition Projection |
|---|---|---|
| How it works | Lists S3 prefixes; creates Glue partition entries | Athena computes partitions from configured pattern |
| When to run | After new partitions are added | Never — auto-computed at query time |
| Scalability | O(n) in partition count; slow for > 100 partitions | O(1) at query time regardless of partition count |
| New partitions | Requires re-running MSCK REPAIR | Auto-included if within the configured range |
| Cost | S3 LIST API calls per partition | No S3 LIST; pattern-based |
| Recommendation | Legacy / small tables | All partitioned tables |

## CTAS output location rules

### Where does CTAS write?

| Workgroup Config | CTAS writes to |
|---|---|
| `EnforceWorkGroupConfiguration=true` + OutputLocation set | The workgroup OutputLocation (overrides everything) |
| `EnforceWorkGroupConfiguration=false` + query has `external_location` | The query's `external_location` |
| `EnforceWorkGroupConfiguration=false` + no `external_location` | The workgroup OutputLocation (if set) or client-side output |

### CTAS table LOCATION after creation

The new table's `LOCATION` in Glue is set to the **actual S3 output
path** (the workgroup result bucket + query subpath), NOT the source
table's location. This means:
- The new table's data lives under the workgroup result bucket.
- Subsequent queries on the new table read from the workgroup result
  bucket.
- If the workgroup result bucket lifecycle policy deletes old query
  results, the CTAS table's data may be deleted.

### CTAS permission requirements

The IAM role running the CTAS needs:
- `glue:CreateTable`, `glue:UpdateDatabase` (on the target database)
- `s3:PutObject`, `s3:AbortMultipartUpload` (on the output bucket)
- `s3:GetObject` (on the source table's data bucket)
- `glue:GetTable`, `glue:GetPartitions` (on the source table)

## Workgroup configuration reference

| Config field | Effect |
|---|---|
| `ResultConfiguration.OutputLocation` | Where all query results (and CTAS output) go |
| `EnforceWorkGroupConfiguration` | `true` = workgroup config overrides client-side; `false` = client can override |
| `BytesScannedCutoffPerQuery` | Per-query byte scan limit; 0 = unlimited |
| `RequesterPaysEnabled` | Allows queries on RequesterPays S3 buckets |
| `EngineVersion.SelectedEngineVersion` | `Athena engine 2` or `Athena engine 3` |
| `PublishCloudWatchMetricsEnabled` | Emit CloudWatch metrics for the workgroup |
| `Configuration.ResultConfiguration.EncryptionConfiguration` | SSE-S3 / SSE-KMS encryption for results |

## Athena engine v2 vs v3 quick reference

| Function / feature | v2 (Presto 0.217) | v3 (Trino 358+) |
|---|---|---|
| Date format | `date_format(col, '%Y-%m-%d')` | `format_datetime(col, 'yyyy-MM-dd')` |
| Date parse | `date_parse(col, '%Y-%m-%d')` | `date_parse(col, 'yyyy-MM-dd')` or `from_iso8601_date(col)` |
| Timestamp parse | `from_iso8601_timestamp(col)` | `from_iso8601_timestamp(col)` (unchanged) |
| Array indexing | 1-indexed | 1-indexed (unchanged) |
| Type coercion | More permissive | Stricter; may reject implicit casts |
| `TRY()` function | Supported | Supported |
| GEOMETRY | Presto functions | Different Trino function names |
| Query timeout | 30 min (DML) | 30 min (DML) |
| DDL timeout | 600 hours | 600 hours |

---

## Step 2: SerDe mismatch and SerDe property error (moved from SKILL.md)

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

---

## Step 3: Stale partitions and partition projection (moved from SKILL.md)

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

---

## Step 7: Format inference error (moved from SKILL.md)

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

---

## SerDe matrix (moved from SKILL.md)

| SerDe class | Format | Handles quoted fields | Column types | Key properties |
|---|---|---|---|---|
| `OpenCSVSerDe` | CSV/Text | Yes (`quoteChar`, `escapeChar`) | ALL columns read as STRING | `separatorChar`, `quoteChar`, `escapeChar` |
| `LazySimpleSerDe` | Delimited Text | No | Native (INT, STRING, etc.) | `field.delim`, `line.delim`, `collection.delim`, `mapkey.delim` |
| `ParquetHiveSerDe` | Parquet | n/a | Native (from Parquet schema) | (ignored) |
| `OrcSerde` | ORC | n/a | Native (from ORC schema) | (ignored) |
| `JsonSerDe` (openx) | JSON (one object per line) | n/a | Native | `ignore.malformed.json` |
| `AvroSerDe` | Avro | n/a | Native (from Avro schema) | `avro.schema.literal` or `avro.schema.url` |

---

## Partition projection properties reference (moved from SKILL.md)

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
