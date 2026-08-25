# Advanced Patterns — Glue Crawler Deployer

Deep-dive content moved verbatim from SKILL.md (progressive disclosure — load on demand).

## Configuration dependency graph (novel heuristic)

Glue Crawler configurations are NOT independent. The IAM role must
exist before the crawler. Lake Formation permissions must be granted
before the crawler can create tables in a Lake Formation-enabled
database. Classifier ordering determines schema inference results.
Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| IAM role | Role exists; `iam:PassRole` permission | role must have glue:CreateTable, glue:UpdateTable, s3:GetObject on the source | crawler can read data + write catalog |
| Data source (S3) | S3 bucket exists; crawler role can read it | crawling a non-existent path creates an empty table or fails silently | schema inference source |
| Data source (DynamoDB) | DynamoDB table exists; role has dynamodb:Scan, dynamodb:DescribeTable | DynamoDB export to S3 is required first; crawler reads from the export in S3 | schema inference from DynamoDB export |
| Data source (JDBC) | Database reachable from Glue; connection exists; role has glue:GetConnection | JDBC connection must be in the same VPC/subnet/security group as the database | schema inference from relational DB |
| Classifiers | Classifier exists (custom) or built-in | ordering is CRITICAL — first match wins; built-in classifiers are always evaluated after custom ones | custom schema inference |
| Catalog database | Glue database exists; crawler role has glue:CreateTable on it | if Lake Formation is enabled, crawler role needs LF permissions on the database | tables created in the correct database |
| Lake Formation | LF permissions granted to crawler role; database is LF-enabled | without LF permissions, crawler FAILS to create or update tables | governed data lake tables |
| Schedule (cron) | Crawler exists; EventBridge scheduler has permission to start crawler | schedule is in UTC; misconfigured cron runs at wrong times | automatic crawl cadence |
| Schedule (event-driven) | S3 Event Notification configured; EventBridge/Lambda trigger exists | missing S3 Event Notification = no trigger fires | event-driven crawl on data arrival |
| Schema merge policy | Crawler exists; ConfigurationOverrides set | "Crawler" behavior is the default; merge affects how multi-table schema conflicts resolve | schema conflict handling |
| Incremental crawl | Crawler has run at least once (needs state) | first run is always full; subsequent runs use incremental state | faster cheaper crawls |

**The classifier-ordering row is the one a baseline model misses.**
Classifiers are evaluated in order — the first match wins. If a custom
Grok classifier is listed AFTER a built-in CSV classifier, and the
file matches both, the CSV result is used, overriding the Grok output.
The procedure below forces an explicit classifier ordering decision.

**Cross-dependency gotchas:**
- The IAM role must be created BEFORE the crawler. The crawler
  references the role ARN at creation time.
- Lake Formation permissions must be granted to the crawler role BEFORE
  the crawler runs. Without LF permissions, table creation fails.
- DynamoDB crawling requires exporting the table to S3 first. The
  crawler reads from the S3 export path, not directly from DynamoDB.
- JDBC crawling requires a Glue Connection (network configuration).
  The crawler uses the connection's VPC/subnet/SG settings.
- Incremental crawl requires at least one successful full crawl to
  establish state. The first run is always full.

## Expert heuristic: incremental crawl vs full crawl trade-off

```text
Full Crawl:
  ├── Reads ALL files in the data source
  ├── Re-creates table schema from scratch
  ├── Slow for large datasets (hours for TB-scale data)
  ├── Always detects schema changes in existing files
  ├── Best for: small datasets, evolving schemas, first run
  └── Cost: high (re-reads everything every time)

Incremental Crawl:
  ├── Reads only NEW or CHANGED files since last crawl
  ├── Preserves existing table schema (does NOT detect schema changes in existing files)
  ├── Fast for append-only workloads
  ├── Requires: at least one full crawl first
  ├── Best for: large append-only datasets (logs, events, streaming sinks)
  └── Cost: low (only reads delta)

Decision matrix:
  ├── Data is append-only (new files added, old files unchanged) → Incremental
  ├── Data schema evolves (existing files may change type) → Full
  ├── Dataset < 10 GB → Full (fast enough, detects schema changes)
  ├── Dataset > 1 TB → Incremental (full would take hours)
  ├── First crawl → Full (always, establishes baseline)
  └── Periodic schema validation needed → Schedule full crawl weekly/monthly
```

**Key implication:** incremental crawl is 10-100x faster than full for
large append-only datasets, but it misses schema changes in existing
files. Schedule periodic full crawls alongside incremental for schema
validation.

## Recent AWS Glue features (2023-2026)

**Recent AWS Glue features (2023-2026):**

- **Incremental crawl improvements (2023-2024):** Enhanced incremental
  crawl with better file change detection using S3 event-time markers.
  Reduced false negatives for schema changes.

- **Partition projection native support (2023-2024):** Glue crawlers
  can now automatically configure partition projection table
  properties when the partition structure is date-range based.

- **Lake Formation tag-based access integration (2023-2024):** Crawlers
  can assign LF-tags to newly created tables, automating tag-based
  access control for discovered data.

- **DynamoDB export to S3 pipeline (2023-2024):** Streamlined DynamoDB
  to S3 export with automatic Glue table creation. The crawler reads
  the DynamoDB JSON export format directly.

- **JDBC crawler performance (2024-2025):** Parallel JDBC crawling for
  large databases with connection pooling, reducing crawl time by up
  to 5x for databases with many tables.

- **Schema change notifications (2024-2025):** EventBridge events fired
  when a crawler detects schema changes, enabling downstream
  pipelines to react automatically.

- **Hudi, Iceberg, Delta Lake support (2024-2025):** Crawlers now
  natively recognize open table formats (Apache Hudi, Apache Iceberg,
  Delta Lake) and create catalog tables with the correct SerDe.

