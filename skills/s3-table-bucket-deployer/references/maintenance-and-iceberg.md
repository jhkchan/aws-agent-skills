# Table Maintenance and Apache Iceberg Features — S3 Table Bucket Deployer

Deep reference on S3 Tables maintenance configuration (compaction,
snapshot management, unreferenced file cleanup — all enabled by default
and per-table configurable), Apache Iceberg features available in S3
Tables (time travel, schema evolution, ACID transactions), Iceberg
format version (v1 vs v2), and partitioning strategy. Loaded on demand
by the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Maintenance configuration fundamentals

### Why S3 Tables maintenance is different from self-managed Iceberg

Self-managed Apache Iceberg on regular S3 requires you to build, deploy,
and operate compaction jobs, snapshot expiration, and orphan file
cleanup yourself. S3 Tables provides ALL THREE as built-in, automatic,
enabled-by-default services. The only decision is whether to keep the
defaults or tune the settings per table.

### The three maintenance types

| Maintenance type | Default | What it does | Key settings |
|---|---|---|---|
| Compaction | ENABLED | Merges small data files into larger files | targetFileSize, minInputFiles, maxInputFiles |
| Snapshot management | ENABLED | Expires old Iceberg snapshots | maxSnapshotAge (seconds), minSnapshots |
| Unreferenced file cleanup | ENABLED | Removes orphaned data files | maxFileAge (seconds) |

### Viewing current maintenance configuration

```bash
aws s3tables get-table-maintenance-configuration \
  --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables \
  --namespace sales_analytics \
  --name orders \
  --region us-east-1
```

### Tuning compaction

Compaction merges small files into larger ones. The default target file
size is ~512 MB. Tune if your workload generates many tiny files or if
you want larger files for scan-heavy workloads.

```bash
aws s3tables update-table-maintenance-configuration \
  --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables \
  --namespace sales_analytics \
  --name orders \
  --type compaction \
  --value '{
    "status": "ENABLED",
    "settings": {
      "targetFileSize": "536870912",
      "minInputFiles": 5,
      "maxInputFiles": 100
    }
  }' \
  --region us-east-1
```

**Setting guidance:**
- `targetFileSize`: 512 MB (536870912 bytes) is a good default. Increase
  to 1 GB for scan-heavy analytical workloads. Decrease for latency-
  sensitive workloads that need faster writes.
- `minInputFiles`: 5 is a good default. Increase to 10 if you want less
  frequent compaction. Set to 1 to compact aggressively (not
  recommended — wastes resources).
- `maxInputFiles`: 100 is a good ceiling. Prevents a single compaction
  job from processing too many files.

### Tuning snapshot management

Snapshot management expires old snapshots, controlling table metadata
growth. Each write operation (INSERT, UPDATE, DELETE, MERGE) creates a
new snapshot. Without expiration, metadata grows unbounded.

```bash
aws s3tables update-table-maintenance-configuration \
  --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables \
  --namespace sales_analytics \
  --name orders \
  --type snapshot-management \
  --value '{
    "status": "ENABLED",
    "settings": {
      "maxSnapshotAge": "604800",
      "minSnapshots": 5
    }
  }' \
  --region us-east-1
```

**Setting guidance:**
- `maxSnapshotAge`: 604800 seconds (7 days) is a good default. Increase
  to 1209600 (14 days) if you need longer time-travel windows. Decrease
  to 86400 (1 day) for high-churn tables with many writes.
- `minSnapshots`: 5 ensures you always retain recent snapshots even if
  they are younger than maxSnapshotAge. Increase to 10 for audit
  requirements.

### Tuning unreferenced file cleanup

Unreferenced file cleanup removes data files that are no longer
referenced by any snapshot (after snapshot expiration). This reclaims
storage.

```bash
aws s3tables update-table-maintenance-configuration \
  --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables \
  --namespace sales_analytics \
  --name orders \
  --type unreferenced-file-removal \
  --value '{
    "status": "ENABLED",
    "settings": {
      "maxFileAge": "2592000"
    }
  }' \
  --region us-east-1
```

**Setting guidance:**
- `maxFileAge`: 2592000 seconds (30 days) is a good default. Files
  older than this that are unreferenced are removed. Decrease for faster
  cleanup (risk: if a long-running transaction references an old file,
  it may fail). Increase for longer retention of orphaned files.

### Disabling maintenance (almost always wrong)

You CAN disable maintenance per-table, but this is almost always the
wrong choice for production:

```bash
# Disabling compaction — NOT recommended
aws s3tables update-table-maintenance-configuration \
  --table-bucket-arn arn:aws:s3tables:us-east-1:123456789012:bucket/analytics-tables \
  --namespace sales_analytics \
  --name orders \
  --type compaction \
  --value '{"status": "DISABLED"}' \
  --region us-east-1
```

**If you disable maintenance, you must:**
- Run your own compaction jobs (or accept small file accumulation).
- Expire snapshots manually (or accept metadata growth).
- Clean up orphaned files (or accept storage cost growth).

In nearly all cases, keeping maintenance ENABLED (even with non-default
settings) is the right choice.

## Apache Iceberg features in S3 Tables

### Time travel

Iceberg maintains a history of snapshots, enabling time-travel queries.
You can query the table as of a previous point in time or a specific
snapshot.

```sql
-- Time travel via Athena: query as of a timestamp
SELECT * FROM sales_analytics.orders
FOR SYSTEM_TIME AS OF TIMESTAMP '2026-08-01 00:00:00';

-- Time travel via Athena: query as of a specific snapshot
SELECT * FROM sales_analytics.orders
FOR SYSTEM_VERSION AS OF 123456789;
```

**Limitation:** time travel only works for snapshots that still exist.
If snapshot management expired old snapshots, you cannot travel beyond
the retention window. The `maxSnapshotAge` and `minSnapshots` settings
determine how far back you can travel.

### Schema evolution

Iceberg supports schema changes without rewriting data files. You can
add columns, rename columns, change column order, and widen types.

```sql
-- Add a column (no rewrite)
ALTER TABLE sales_analytics.orders ADD COLUMNS (discount double);

-- Rename a column (no rewrite)
ALTER TABLE sales_analytics.orders RENAME COLUMN status TO order_status;

-- Drop a column (metadata-only, data not immediately removed)
ALTER TABLE sales_analytics.orders DROP COLUMN discount;
```

**Key:** schema evolution is metadata-only. Existing data files are not
rewritten. Old files have null values for newly added columns. This is a
core Iceberg feature — schema changes are O(1) metadata operations.

### ACID transactions

Iceberg provides ACID guarantees on S3 Tables. Each write operation
(create, update, delete, merge) is atomic — it either fully commits or
fully rolls back.

```sql
-- ACID UPDATE (requires Iceberg v2)
UPDATE sales_analytics.orders
SET status = 'shipped'
WHERE order_id = 12345;

-- ACID DELETE (requires Iceberg v2)
DELETE FROM sales_analytics.orders
WHERE order_date < '2025-01-01';

-- ACID MERGE (upsert — requires Iceberg v2)
MERGE INTO sales_analytics.orders t
USING (SELECT * FROM staging_orders) s
ON t.order_id = s.order_id
WHEN MATCHED THEN UPDATE SET status = s.status
WHEN NOT MATCHED THEN INSERT *;
```

**Key:** ACID operations require Iceberg v2 format. v1 tables support
only append and overwrite (no row-level operations).

## Iceberg format version: v1 vs v2

### Feature comparison

| Feature | v1 | v2 |
|---|---|---|
| Append (INSERT INTO) | Yes | Yes |
| Overwrite | Yes | Yes |
| Row-level deletes (DELETE) | No | Yes |
| Row-level updates (UPDATE) | No | Yes |
| MERGE INTO (upsert) | No | Yes |
| Equality deletes | No | Yes |
| Position deletes | No | Yes |

### Recommendation

Use Iceberg v2 for all new tables unless there is a specific downstream
compatibility constraint. v2 is a superset of v1 — all v1 features work
in v2 tables. The row-level operations (UPDATE, DELETE, MERGE INTO) are
essential for most production analytics workloads.

### Specifying format version at creation

```json
{
  "iceberg": {
    "schema": { ... },
    "partition-spec": [ ... ],
    "format-version": 2
  }
}
```

Omitting `format-version` may default to v1 depending on the client.
Always specify `format-version: 2` explicitly for new tables.

## Partitioning strategy

### Choosing partition columns

The partition spec determines how data is physically laid out. Good
partitioning enables file pruning (skipping irrelevant files), which is
the single biggest factor in Iceberg query performance.

```text
Query pattern → Partition strategy:
  ├── Time-series: WHERE order_date >= '2026-01-01'
  │     → day(order_date) or month(order_date)
  ├── Category filter: WHERE region = 'us-east'
  │     → identity(region) for low cardinality (<1000 values)
  ├── High-cardinality lookup: WHERE customer_id = 12345
  │     → bucket[16](customer_id) or bucket[32](customer_id)
  ├── Geo-temporal: WHERE date = '2026-08-01' AND region = 'us'
  │     → day(date), truncate[2](region) [composite]
  └── No common filter pattern
        → day(timestamp_column) as a safe default
```

### Partition cardinality rules

| Partition strategy | Max partitions | When to use |
|---|---|---|
| day(timestamp) | ~365/year per table | Most common; daily queries |
| month(timestamp) | ~12/year per table | Moderate volume; monthly reporting |
| hour(timestamp) | ~8760/year per table | Very high volume; real-time dashboards |
| identity(low-card) | = distinct values | Categories (<1000 values) |
| bucket[N](column) | N (fixed) | High-cardinality columns |

**Rule of thumb:** target each partition to hold at least 100 MB of
data. Too many partitions with too little data = small file problem.
Too few partitions with too much data = full scan problem.

### Hidden partitioning

Iceberg uses "hidden partitioning" — you partition by a transform of a
column, but queries filter on the original column. Iceberg automatically
prunes files based on the partition spec.

```text
Schema column: order_date (timestamp)
Partition spec: day(order_date) → hidden partition column: order_date_day

Query: SELECT * FROM orders WHERE order_date >= '2026-08-01'
→ Iceberg prunes to only partitions where order_date_day >= 2026-08-01
→ Skips all data files from older partitions
```

This means you do NOT need to change your SQL to match the partition
spec. Iceberg handles the mapping automatically.

## Terraform example

```hcl
resource "aws_s3tables_table_bucket" "analytics" {
  name   = "analytics-tables"
  region = "us-east-1"
}

resource "aws_s3tables_namespace" "sales" {
  table_bucket_arn = aws_s3tables_table_bucket.analytics.arn
  namespace        = "sales_analytics"
}

resource "aws_s3tables_table" "orders" {
  table_bucket_arn = aws_s3tables_table_bucket.analytics.arn
  namespace        = aws_s3tables_namespace.sales.namespace
  name             = "orders"
  format           = "ICEBERG"

  metadata = jsonencode({
    iceberg = {
      schema = {
        type = "struct"
        fields = [
          { id = 1, name = "order_id",     type = "long",      required = true }
          { id = 2, name = "customer_id",  type = "long",      required = true }
          { id = 3, name = "order_date",   type = "timestamp", required = true }
          { id = 4, name = "amount",       type = "double",    required = false }
          { id = 5, name = "status",       type = "string",    required = false }
        ]
      }
      partition-spec = [
        { name = "order_date_day", transform = "day", source-id = 3 }
      ]
      format-version = 2
    }
  })
}
```

## Common maintenance pitfalls

1. **Disabling maintenance without a replacement plan.** If you disable
   compaction, snapshot management, or file cleanup, you must operate
   these yourself. Most teams are better off keeping defaults enabled.

2. **Setting minSnapshots too low.** If you set minSnapshots to 1, you
   lose time-travel capability almost immediately after each write.
   Keep at least 5 for short-term rollback safety.

3. **Setting maxSnapshotAge too long.** If you set maxSnapshotAge to
   90+ days, metadata grows significantly. This slows down query
   planning and increases cost. 7-14 days is typical.

4. **Ignoring compaction settings for write-heavy tables.** High-volume
   ingestion tables generate many small files. Consider lowering
   minInputFiles to trigger compaction more aggressively for these
   tables.

5. **Forgetting that maintenance is per-table.** Each table has its own
   maintenance configuration. Configuring maintenance on one table does
   NOT apply to others. Review each table's settings.
