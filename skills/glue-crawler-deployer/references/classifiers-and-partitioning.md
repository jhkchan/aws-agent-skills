# Classifiers and Partitioning — Glue Crawler Deployer

Deep reference on classifier configuration and ordering (Grok, JSON,
CSV, XML; first-match-wins semantics; built-in vs custom), partition
discovery vs partition projection (folder enumeration, projection
configuration, Athena integration), and schema merge policy behavior.
Loaded on demand by the skill — kept out of the main SKILL.md body so
the provisioning procedure stays scannable.

## Classifier fundamentals

### Evaluation order

Glue Crawler evaluates classifiers in a strict order:

```text
1. Custom classifiers in the ORDER listed in the crawler's
   Classifiers field. Position 0 is evaluated first.
2. Built-in classifiers (in fixed order):
   a. ORC
   b. Parquet
   c. Avro
   d. JSON
   e. CSV
   f. XML

First match wins. Once a classifier matches a file, its schema is
used and no further classifiers are evaluated for that file.
```

### Why ordering matters

If a file matches both a custom classifier and a built-in one, the
custom classifier listed FIRST wins. If the custom classifier is
listed AFTER the built-in, the built-in result is used.

```text
Example: log file "app-2026-08-05.log"
  ├── Matches custom Grok classifier (designed for this log format)
  └── Matches built-in CSV classifier (treats lines as CSV)

  Classifiers list: ["AppLogGrok"]  → Grok schema used ✓
  Classifiers list: []               → CSV schema used (built-in) ✗
  Classifiers list: ["AppLogGrok", "CustomCsv"]
                     → Grok evaluated first; if match, Grok used ✓
```

### Grok classifier in detail

Grok classifiers parse unstructured log lines using Grok patterns.

```bash
aws glue create-grok-classifier \
  --name "AppLogGrok" \
  --classification "app-logs" \
  --grok-pattern "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{DATA:service} %{GREEDYDATA:message}" \
  --custom-patterns "LOGLEVEL [DEBUG|INFO|WARN|ERROR|FATAL]"
```

**Grok pattern syntax:**
- `%{PATTERN_NAME:field_name}` — captures a named field
- `%{DATA:field}` — non-greedy match for any data
- `%{GREEDYDATA:field}` — greedy match for remaining text
- Custom patterns defined in `--custom-patterns` as `NAME pattern`

### JSON classifier in detail

JSON classifiers specify a JSON path to the array of records within a
nested JSON structure.

```bash
aws glue create-json-classifier \
  --name "EventsJsonClassifier" \
  --json-path "$.events[*]"
```

Without a JSON classifier, the built-in JSON classifier creates a
table with one row per JSON file. With a JSON path, it creates one
row per element in the specified array.

### CSV classifier in detail

CSV classifiers customize delimiter, quote character, and header
handling.

```bash
aws glue create-csv-classifier \
  --name "PipeDelimitedClassifier" \
  --delimiter "|" \
  --quote-symbol "\"" \
  --contains-header "PRESENT" \
  --header "id,name,value,timestamp,category"
```

### XML classifier in detail

XML classifiers specify the row tag (the XML element representing one
record).

```bash
aws glue create-xml-classifier \
  --name "OrdersXmlClassifier" \
  --classification "orders-xml" \
  --row-tag "order"
```

## Partition discovery vs partition projection

### Folder partitioning (default)

The crawler discovers partitions by enumerating folder values that
match the `key=value` naming convention.

```text
S3 structure:
  s3://bucket/events/
    year=2026/
      month=08/
        day=05/
          data-001.json
          data-002.json
        day=04/
          data-001.json

Crawler behavior:
  → Enumerates ALL year=, month=, day= folders
  → Creates partition objects in the Data Catalog
  → Each partition = one catalog entry
  → 365 days × 1 partition/day = 365 catalog entries per year
```

**Cost implications:**
- Crawler time increases linearly with partition count (must LIST
  every folder).
- Athena `GetPartitions` API call returns all partitions (slow for
  10,000+ partitions).
- Data Catalog storage charges per partition.

### Partition projection (configured)

Partition projection eliminates partition enumeration. Athena
COMPUTES partition values from a configured range.

```json
{
  "projection.enabled": "true",
  "projection.year.type": "integer",
  "projection.year.range": "2024,2026",
  "projection.month.type": "integer",
  "projection.month.range": "01,12",
  "projection.month.digits": "2",
  "projection.day.type": "date",
  "projection.day.format": "yyyy-MM-dd",
  "projection.day.range": "2024-01-01,NOW",
  "storage.location.template": "s3://my-data-lake/events/year=${year}/month=${month}/day=${day}"
}
```

**How it works:**
1. Athena query filters (e.g., `WHERE year=2026 AND month=08`).
2. Athena uses the projection config to compute valid partition values.
3. Athena constructs the S3 path from the storage.location.template.
4. No `GetPartitions` API call needed. No partition objects in catalog.

**Supported projection types:**
- `integer` — numeric range (e.g., `2024,2026`)
- `date` — date range with format (e.g., `2024-01-01,NOW`)
- `enum` — explicit list (e.g., `A,B,C`)
- `injected` — value passed in query (no range validation)

### When to use which

| Criteria | Folder partitioning | Partition projection |
|---|---|---|
| Partition values are a known range (dates, enums) | Works but costly | Ideal — zero enumeration |
| Partition values are arbitrary (user IDs, hashes) | Works | Does NOT work (cannot project arbitrary values) |
| Number of partitions < 20,000 | Fine | Better |
| Number of partitions > 20,000 | Slow, costly | Strongly recommended |
| Athena query performance matters | Acceptable | Significantly faster |

### Partition projection with multiple crawlers

If multiple crawlers write to the same database, use partition
projection on tables with range-based partitions to avoid partition
conflicts between crawlers.

## Schema merge policy

### MergeNewColumns (default)

Adds new columns found in any file to the existing table schema. Does
NOT remove old columns or change existing column types.

```text
Before crawl: Table { id: int, name: string }
New file has:  { id: int, name: string, email: string, age: int }
After crawl:   Table { id: int, name: string, email: string, age: int }
```

Safe for heterogeneous data. Never drops columns.

### UpdateNewColumns

Same as MergeNewColumns for adding new columns. Also updates column
TYPES if the new file has a different type for an existing column.

```text
Before crawl: Table { id: int, name: string }
New file has:  { id: bigint, name: string, email: string }
After crawl:   Table { id: bigint, name: string, email: string }
```

Use when schema types evolve.

### UpdateAll

Replaces the entire schema with the latest file's schema. Removes
columns not present in the latest file.

```text
Before crawl: Table { id: int, name: string, email: string }
New file has:  { id: int, name: string }
After crawl:   Table { id: int, name: string }
(email column REMOVED)
```

Use only for homogeneous data where all files have the same schema.

## Terraform example

```hcl
resource "aws_glue_classifier" "app_log_grok" {
  name = "AppLogGrok"

  grok_classifier {
    classification  = "app-logs"
    grok_pattern    = "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{DATA:service} %{GREEDYDATA:message}"
    custom_patterns = "LOGLEVEL [DEBUG|INFO|WARN|ERROR|FATAL]"
  }
}

resource "aws_glue_catalog_database" "analytics" {
  name = "analytics_db"
}

resource "aws_glue_crawler" "events" {
  name          = "events-crawler"
  database_name = aws_glue_catalog_database.analytics.name
  role          = aws_iam_role.glue_crawler.arn
  classifiers   = [aws_glue_classifier.app_log_grok.name]
  table_prefix  = "raw_"

  s3_target {
    path = "s3://my-data-lake/events/"
  }

  recrawl_policy {
    recrawl_behavior = "CRAWL_INCREMENTAL"
  }

  schema_change_policy {
    delete_behavior = "DEPRECATE_IN_DATABASE"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  schedule = "cron(0 2 * * ? *)"

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Tables = {
        AddOrUpdateBehavior = "MergeNewColumns"
      }
      Partitions = {
        EnablePartitionDiscoveryForBuckets = true
      }
    }
  })

  tags = {
    Environment = "production"
    DataSource  = "s3-events"
  }
}
```
