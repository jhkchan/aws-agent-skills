# Advanced Patterns — Firehose Delivery Stream Deployer

Expert-heuristic deep dives and recent-feature notes, moved verbatim from SKILL.md. Load on demand.

## Expert heuristic: buffering hints trade-off (latency vs cost)
A baseline model says "use default buffering." The correct heuristic
recognizes that buffering hints are a tunable trade-off between
delivery latency and cost (number of destination writes).

```text
Buffering hints (S3 destination):
  SizeInMBs:    1-128 MB (default 5 MB for S3; 64 MB for Parquet)
  IntervalInSeconds: 60-900 seconds (default 300)

  LOW buffering (1 MB / 60s):
    → Many small S3 objects (high PUT cost, many tiny Parquet files)
    → Low latency (data delivered quickly)
    → Bad for Athena (many small files = slow queries)
    → Good for real-time dashboards

  HIGH buffering (128 MB / 900s):
    → Few large S3 objects (low PUT cost, optimal Parquet row groups)
    → High latency (up to 15 minutes)
    → Good for Athena (fewer files = faster queries)
    → Bad for real-time dashboards

  RECOMMENDED for Parquet (Athena下游):
    SizeInMBs: 64-128 MB (Parquet row group optimization)
    IntervalInSeconds: 300-900s

  RECOMMENDED for OpenSearch:
    SizeInMBs: 5 MB (avoid bulk indexing overhead)
    IntervalInSeconds: 60-300s
```

**Key implication:** for S3 destinations queried by Athena, use larger
buffers (64-128 MB) to produce fewer, larger Parquet files. For
OpenSearch destinations, use smaller buffers (5 MB) to reduce indexing
latency. The defaults are rarely optimal.

## Expert heuristic: Lambda transformation blueprints
Lambda transformation processes each batch of records. The Lambda
function receives a base64-encoded payload and must return transformed
records plus any failed records.

```text
Lambda transformation flow:
  Firehose → batch of records → Lambda invocation
    → Lambda transforms each record (parse, enrich, filter)
    → Lambda returns: { records: [...], droppedRecords: [...] }
    → Transformed records continue to format conversion / destination
    → Dropped records are silently discarded (enable backup to retain)

  Common transformation blueprints:
    1. JSON parsing + field extraction (data normalization)
    2. Enrichment (add GeoIP, lookup reference data)
    3. Filtering (drop records not matching criteria)
    4. Format conversion prep (ensure records are valid JSON for Parquet)
    5. Aggregation (combine multiple records into one)
```

**Key implication:** if using format conversion to Parquet, the Lambda
transformation MUST output valid JSON that matches the Glue table
schema. Malformed JSON from Lambda causes format conversion to fail —
records go to the S3 error prefix, not the main prefix.

## Expert heuristic: S3 partition projection via Hive-style prefix
S3 prefix patterns determine data partitioning. Hive-style prefixes
enable Athena partition pruning and Glue partition projection.

```text
Flat prefix (BAD for analytics):
  S3 key: my-bucket/data/2024-01-15-10-30-00-recordId.parquet
  → Every Athena query scans ALL files (no partition pruning)
  → Slow queries, high cost

Hive-style prefix (GOOD for analytics):
  S3 prefix: my-bucket/data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/
  S3 key: my-bucket/data/year=2024/month=01/day=15/2024-01-15-10-30-00-recordId.parquet
  → Athena can prune by year/month/day (scan less data)
  → Glue crawler auto-discovers partitions
  → Partition projection can auto-populate partitions

Error prefix (for failed records):
  Error prefix: my-bucket/errors/!{firehose:error-output-type}/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/
  → Failed records separated by error type and date
```

**Key implication:** always use Hive-style partitioned prefixes for
S3 destinations queried by Athena. The Firehose expression syntax
(`!{timestamp:yyyy}`) is specific to Firehose — do not use generic
template variables.

## Step 13 — Recent features
- **Parquet and ORC format conversion (2023-2024):** Built-in format
  conversion using Glue table schemas — no custom code needed. Enables
  direct Firehose-to-Athena pipelines with columnar formats.

- **MSK as a direct source (2023-2024):** Firehose can read directly
  from Amazon MSK topics without a separate consumer. Simplifies
  Kafka-to-S3/OpenSearch pipelines.

- **CloudWatch Logs subscription to Firehose (2023-2024):** Direct
  subscription filter integration for log processing and SIEM
  ingestion. No Lambda intermediary needed.

- **Partition projection support (2024-2025):** Hive-style S3 prefixes
  with `!{timestamp:...}` expressions enable Athena partition
  projection auto-population, eliminating the need for manual partition
  management.

- **HTTP endpoint destination enhancements (2024-2025):** Improved
  Splunk HEC integration with buffered delivery and per-record
  metadata support. Extended timeout for slow endpoints.

- **Enhanced fan-out for KDS source (2024-2025):** Firehose can use
  enhanced fan-out consumers when reading from Kinesis Data Streams,
  providing dedicated throughput for high-volume pipelines.
