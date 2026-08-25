---
name: glue-crawler-deployer
description: 'Provisions AWS Glue Crawlers with production defaults: data source configuration (S3, DynamoDB, JDBC), IAM role with least-privilege permissions, classifier configuration with correct ordering (Grok, JSON, CSV — first match wins), schema merge policy, partitioning strategy (folder partitioning vs partition projection for cost reduction), Lake Formation integration, catalog database target, scheduling (cron, event-driven via S3 Event Notifications), incremental vs full crawl trade-off, schema evolution handling, and DynamoDB export crawling. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Glue Crawler, configuring crawl schedules, setting up custom classifiers, integrating with Lake Formation, or configuring partition projection. Triggers: create glue crawler, glue crawler classifier, glue crawler schedule, glue crawler lake formation, glue crawler partition projection, glue dynamodb crawler, glue jdbc crawler.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with glue access (glue:CreateCrawler, glue:StartCrawler, iam:PassRole). Works with Terraform aws_glue_crawler / aws_glue_classifier resources and CloudFormation AWS::Glue::Crawler templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, glue, glue-crawler, cloudops, deploy, analytics, provisioning, classifier, partition-projection, lake-formation, data-catalog, schema-discovery
  dependencies: aws-orchestrator
  keywords: aws, glue, glue crawler, crawler, data catalog, classifier, cloudops, deploy, provisioning, lake formation, partition projection, schema discovery, s3 crawler, dynamodb crawler, jdbc crawler
  when_to_use: Invoke when the user wants to create a Glue Crawler, configure custom classifiers (Grok, JSON, CSV), set up crawl schedules (cron or event-driven via S3 Event Notifications), integrate with Lake Formation, configure partition projection for cost reduction, handle schema evolution, choose incremental vs full crawl, or configure DynamoDB/JDBC data source crawling. Do NOT invoke for Glue ETL jobs (use glue-job-troubleshooter), Glue DataBrew, or auditing existing Glue crawlers (use glue-crawler-job-auditor).
---

# Glue Crawler Deployer

An AWS CloudOps agent skill that provisions AWS Glue Crawlers with
production-grade defaults. The skill walks the operator through data
source selection (S3, DynamoDB, JDBC), IAM role creation with least-
privilege permissions, classifier configuration and ordering (first
match wins), schema merge policy, partitioning strategy (folder-based
vs partition projection), Lake Formation integration, catalog database
target, scheduling decisions (cron vs event-driven), incremental vs
full crawl trade-off, schema evolution handling, and output table
configuration, captures all decisions, explains why each default
matters, and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create Glue Crawler, Glue Crawler classifier, Glue Crawler schedule,
Glue Crawler Lake Formation, Glue Crawler partition projection, Glue
DynamoDB Crawler, Glue JDBC Crawler.

## STRICT output contract

When this skill is invoked with a Glue Crawler-provisioning request
(create a crawler, configure classifiers, set up a crawl schedule,
integrate Lake Formation, configure partition projection, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `GLUE_CRAWLER:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Data source (S3, DynamoDB, JDBC) | Choose source type |
| Step 2 — IAM role and permissions | Security posture |
| Step 3 — Classifiers (Grok, JSON, CSV) | Custom schema inference |
| Step 4 — Schema merge policy | How schema changes are applied |
| Step 5 — Partitioning strategy | Folder vs partition projection |
| Step 6 — Lake Formation integration | Data lake governance |
| Step 7 — Catalog database target | Where tables land |
| Step 8 — Scheduling (cron vs event-driven) | When crawls run |
| Step 9 — Incremental vs full crawl | Crawl scope trade-off |
| Step 10 — Schema evolution handling | Schema change resilience |
| Step 11 — Output table configuration | Prefix/suffix, table-level |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/classifiers-and-partitioning.md | Classifier + partition deep dive |
| references/iam-and-lake-formation.md | IAM + Lake Formation detail |

## Mindset

**One-line takeaway:** A Glue Crawler infers schema from data and
registers tables in the Glue Data Catalog. Its correctness depends on
classifier ordering (first match wins), partition strategy (projection
avoids costly partition enumeration), and schema merge policy (how
conflicts between old and new schema are resolved). Misconfiguration
leads to wrong table schemas, missed partitions, and broken downstream
Athena queries.

Three misconceptions dominate Glue Crawler misdesign at provisioning
time:

- **"Classifiers are evaluated alphabetically."** They are NOT.
  Classifiers in the crawler's `Classifiers` list are evaluated in
  ORDER. The FIRST classifier that matches wins. If a Grok classifier
  matches a log file before the built-in CSV classifier, the Grok
  result is used. Ordering is critical.

- **"Full crawl is always safer."** Full crawl is expensive for large
  datasets — it re-reads ALL files, not just new ones. Incremental
  crawl only reads new or changed files since the last crawl, reducing
  cost and time. But incremental crawl may miss schema changes in
  existing files. The trade-off depends on whether the data evolves.

- **"Folder partitioning is the only option."** Partition PROJECTION
  is often better for high-cardinality partitions (e.g., per-hour or
  per-minute partitions). Folder partitioning creates a physical
  partition per value, requiring crawler enumeration. Partition
  projection computes partition values on-the-fly from a configured
  range, eliminating enumeration cost.

## Configuration dependency graph (novel heuristic)

Full dependency table and cross-dependency gotchas moved to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand when sequencing provisioning.

## Expert heuristic: classifier order evaluation (first match wins)

Evaluation-order diagram moved to [references/classifiers-and-partitioning.md](references/classifiers-and-partitioning.md) — load on demand when configuring classifiers.

## Expert heuristic: partition projection for cost reduction

Folder-vs-projection comparison moved to [references/classifiers-and-partitioning.md](references/classifiers-and-partitioning.md) — load on demand when choosing a partitioning strategy.

## Expert heuristic: incremental crawl vs full crawl trade-off

Full-vs-incremental decision tree moved to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand when choosing crawl scope.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| S3 data source exists | Crawler needs a reachable S3 path | `aws s3 ls s3://<bucket>/<path>/` |
| DynamoDB table exists (if DynamoDB source) | DynamoDB crawling reads from S3 export | `aws dynamodb describe-table --table-name <name>` |
| JDBC database reachable (if JDBC source) | Glue Connection needs VPC access | Verify Glue Connection exists and tests successfully |
| Glue database exists (catalog target) | Crawler creates tables in a database | `aws glue get-database --name <db-name>` |
| IAM role with correct permissions | Crawler reads data and writes catalog | Verify role trust policy + permissions policy |
| Lake Formation permissions (if LF-enabled) | LF-enabled DB requires crawler role grants | `aws lakeformation list-permissions` |
| S3 Event Notification (if event-driven) | Event-driven crawl needs trigger configured | `aws s3api get-bucket-notification-configuration --bucket <name>` |
| Classifier definitions (if custom) | Custom classifiers must exist before crawler | `aws glue get-classifier --name <name>` |

## Step 1 — Data source (S3, DynamoDB, JDBC)

| Source | Configuration | Notes |
|---|---|---|
| S3 | `S3Targets` with `Path: s3://bucket/path/` | Most common; supports partitioned folders |
| DynamoDB | Export to S3 first; crawl the S3 export path | DynamoDB crawler reads from S3 export, not directly from DynamoDB |
| JDBC | `JdbcTargets` with `ConnectionName` and `Path` | Requires Glue Connection for VPC/network access |

**S3 data source:**

```json
{
  "Targets": {
    "S3Targets": [
      { "Path": "s3://my-data-lake/events/year=2026/" }
    ]
  }
}
```

**DynamoDB export crawl:** DynamoDB tables must be exported to S3
(using `export-table-to-point-in-time` with `--export-format DYNAMODB_JSON`).
The crawler reads from the S3 export path, not directly from DynamoDB.
Export to `s3://my-ddb-exports/dynamodb/MyTable/` then point the
crawler at that path.

## Step 2 — IAM role and permissions

The crawler needs an IAM role with trust policy (Glue service) and
permissions policy (read data source, write to catalog).

Trust and permissions policy JSON moved to [references/iam-and-lake-formation.md](references/iam-and-lake-formation.md) — load on demand when creating the crawler role.

**Critical:** scope S3 permissions to the specific bucket/path. Do NOT
use `Resource: "*"`. Scope Glue permissions to the specific database.

## Step 3 — Classifiers (Grok, JSON, CSV)

Classifiers define how the crawler infers schema. Custom classifiers
are evaluated in ORDER before built-in classifiers. First match wins.

| Classifier type | Use case | Configuration |
|---|---|---|
| Grok | Custom log parsing | Grok pattern, custom labels |
| JSON | Nested JSON files | JSON path |
| CSV | Custom delimiters, headers | Delimiter, quote character, column headers |
| XML | XML structure | XML path, row tag |

Classifier creation CLI moved to [references/classifiers-and-partitioning.md](references/classifiers-and-partitioning.md) — load on demand when creating custom classifiers.

**Attach classifiers to crawler (ORDER matters):**

```json
{
  "Classifiers": ["AppLogClassifier", "CustomCsvClassifier"]
}
```

Built-in classifiers (CSV, JSON, ORC, Parquet) are evaluated AFTER
all custom classifiers. If no custom classifier matches, the built-in
classifiers are tried.

## Step 4 — Schema merge policy

The schema merge policy controls how schema conflicts are resolved when
a crawler finds different schemas in different files within the same
table.

| Policy | Behavior | Use case |
|---|---|---|
| `Crawler` (default) | Keeps the most recent schema; adds new columns, does not remove old | General purpose, append-only |
| `MERGE` | Merges schemas from all files; keeps all columns seen across files | Data with evolving columns |
| `UPDATE_IN_PLACE` | Replaces schema entirely with the latest file's schema | Homogeneous data, latest-wins |

**Configure via crawler schema change config:**

```json
{
  "ConfigurationOverrides": {
    "CrawlerOutput": {
      "Tables": {
        "AddOrUpdateBehavior": "MergeNewColumns"
      }
    }
  }
}
```

Options: `MergeNewColumns` (default), `UpdateNewColumns`, `UpdateAll`.

## Step 5 — Partitioning strategy

| Strategy | How it works | Best for |
|---|---|---|
| Folder partitioning | Crawler enumerates folder values as partitions | Arbitrary partition values |
| Partition projection | Athena computes partitions from configured range | Date/range/enum partitions |

Partition projection table properties moved to [references/classifiers-and-partitioning.md](references/classifiers-and-partitioning.md) — load on demand when configuring projection.

Partition projection eliminates the need for crawler-created partition
entries. Athena computes the partition list from the configured range.

## Step 6 — Lake Formation integration

If the Glue Data Catalog database is Lake Formation-enabled, the
crawler role needs LF permissions.

Lake Formation grant commands moved to [references/iam-and-lake-formation.md](references/iam-and-lake-formation.md) — load on demand for LF-enabled databases.

**Critical:** without LF permissions, the crawler fails with
`AccessDeniedException` when trying to create or update tables in an
LF-enabled database.

## Step 7 — Catalog database target

The crawler creates tables in the specified Glue database.

```json
{
  "DatabaseName": "my_database",
  "Targets": {
    "S3Targets": [{ "Path": "s3://my-data-lake/events/" }]
  }
}
```

Ensure the database exists before creating the crawler:

```bash
aws glue create-database --database-input Name=my_database
```

## Step 8 — Scheduling (cron vs event-driven)

| Schedule type | Configuration | Best for |
|---|---|---|
| Cron | `Schedule: "cron(0 2 * * ? *)"` (daily at 2 AM UTC) | Regular cadence |
| Event-driven | S3 Event Notification + EventBridge/Lambda trigger | Crawl on data arrival |
| On-demand | No schedule; manual `StartCrawler` | Ad-hoc, testing |

**Cron schedule:**

```json
{
  "Schedule": {
    "ScheduleExpression": "cron(0 2 * * ? *)"
  }
}
```

**Event-driven crawl (S3 Event Notification):** Configure S3 Event
Notification to trigger a Lambda/EventBridge rule that calls
`glue:StartCrawler` on new object creation. Use `put-bucket-notification-configuration`
with `LambdaFunctionConfigurations` filtered by prefix/suffix.

## Step 9 — Incremental vs full crawl

Configure via the `RecrawlPolicy` setting:

```json
{
  "RecrawlPolicy": {
    "RecrawlBehavior": "CRAWL_INCREMENTAL"
  }
}
```

Options: `CRAWL_EVERYTHING` (full) or `CRAWL_INCREMENTAL`.

Incremental crawl requires at least one full crawl to establish state.
The first run is always full. Subsequent runs only process new or
changed files.

## Step 10 — Schema evolution handling

| Scenario | Behavior | Recommendation |
|---|---|---|
| New column added | `MergeNewColumns` adds it | Default; works well |
| Column type changed | Conflict — may keep old type | `UpdateAll` to force latest |
| Column removed | Depends on merge policy | `MergeNewColumns` keeps old |
| Nested schema changes | Complex; may create new struct | Test with data |

**Best practice:** use `MergeNewColumns` for append-only data (safe
default). Use `UpdateAll` only for homogeneous data wanting latest-wins.

## Step 11 — Output table configuration

```json
{
  "TablePrefix": "raw_",
  "ConfigurationOverrides": { "CrawlerOutput": { "Tables": { "TableThreshold": 100 } } }
}
```

`TablePrefix` prepends to all table names (useful when multiple
crawlers write to the same database). `TableThreshold` (default
1,000,000): the number of files required to form a table.

## Step 12 — Recent features

Recent feature notes moved to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## NEVER do these things

1. **NEVER ignore classifier ordering.** Classifiers are evaluated in
   ORDER. The first match wins. Built-in classifiers run after custom
   ones. If your custom classifier is not matching, check that a
   built-in classifier is not matching first.

2. **NEVER grant `Resource: "*"` for S3 in the crawler IAM role.**
   Scope S3 permissions to the specific bucket and path. Least-
   privilege prevents the crawler from reading unintended data.

3. **NEVER skip Lake Formation permissions for LF-enabled databases.**
   Without LF permissions, the crawler fails with `AccessDeniedException`
   when creating tables. Grant LF permissions to the crawler role
   before running.

4. **NEVER crawl DynamoDB directly.** DynamoDB crawling requires
   exporting to S3 first. The crawler reads from the S3 export path,
   not from DynamoDB. Use the DynamoDB export-to-S3 feature.

5. **NEVER use full crawl for large append-only datasets.** Full crawl
   re-reads ALL files every run. Use incremental crawl for append-only
   data. Schedule periodic full crawls (weekly/monthly) for schema
   validation.

6. **NEVER assume folder partitioning is the only option.** For date-
   range or well-structured partitions, use partition projection. It
   eliminates crawler partition enumeration and Athena GetPartitions
   costs.

7. **NEVER forget the Glue Connection for JDBC crawlers.** JDBC
   crawling requires a Glue Connection (VPC, subnet, security group).
   The crawler uses the connection's network settings. Without it, the
   crawler cannot reach the database.

8. **NEVER use `UpdateAll` merge behavior on heterogeneous data.**
   `UpdateAll` replaces the schema with the latest file's schema. If
   files have different schemas, this drops columns. Use
   `MergeNewColumns` for heterogeneous data.

9. **NEVER create a crawler without a catalog database.** The crawler
   needs a target database to create tables in. Create the database
   first (`aws glue create-database`).

10. **NEVER assume the first crawl is incremental.** The first crawl
    is ALWAYS full, regardless of the RecrawlPolicy setting.
    Incremental crawl requires prior state from a full crawl.

## Output format

```text
GLUE_CRAWLER: <crawler-name> (<data-source>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Crawler name: <name>
  [✓|✗] Data source: <S3 | DynamoDB-export | JDBC> (<path-or-connection>)
  [✓|✗] IAM role: <role-name> (trust: glue, scoped: <s3-bucket>)
  [✓|✗] Classifiers: <list, ordered> (first-match-wins)
  [✓|✗] Schema merge policy: MergeNewColumns | UpdateAll
  [✓|✗] Partitioning: folder | partition-projection (<keys>)
  [✓|✗] Lake Formation: enabled (LF permissions granted) | disabled
  [✓|✗] Catalog database: <database-name>
  [✓|✗] Schedule: <cron-expression> | event-driven | on-demand
  [✓|✗] Crawl mode: incremental | full
  [✓|✗] Table prefix: <prefix> | none
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws glue get-crawler --name <crawler-name>
  aws glue get-table --database-name <database-name> --name <table-name>
  aws glue get-classifier --name <classifier-name>
```

### Worked example — S3 events crawler with custom JSON classifier

```text
GLUE_CRAWLER: events-crawler (S3: s3://my-data-lake/events/)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Crawler name: events-crawler
  [✓] Data source: S3 (s3://my-data-lake/events/year=2026/)
  [✓] IAM role: GlueCrawlerRole (trust: glue, scoped: my-data-lake/events/*)
  [✓] Classifiers: ["EventsJsonClassifier"] (first-match-wins before built-in JSON)
  [✓] Schema merge policy: MergeNewColumns
  [✓] Partitioning: partition-projection (year, month, day)
  [✓] Lake Formation: enabled (LF permissions: CREATE_TABLE, ALTER on my_database)
  [✓] Catalog database: analytics_db
  [✓] Schedule: cron(0 2 * * ? *) (daily at 2 AM UTC)
  [✓] Crawl mode: incremental
  [✓] Table prefix: raw_
  [✓] Tags: Environment=production, DataSource=s3-events
VERIFICATION_COMMANDS:
  aws glue get-crawler --name events-crawler
  aws glue get-table --database-name analytics_db --name raw_events
  aws glue get-classifier --name EventsJsonClassifier
```

## Error handling

Error deep dives moved to [references/error-handling.md](references/error-handling.md) — load on demand when a crawl fails or misbehaves.

## References (load on demand)

- [references/classifiers-and-partitioning.md](references/classifiers-and-partitioning.md) — classifier ordering heuristics, partition projection patterns, classifier creation CLI, projection table properties.
- [references/iam-and-lake-formation.md](references/iam-and-lake-formation.md) — crawler IAM trust and permissions policies, Lake Formation grant commands.
- [references/advanced-patterns.md](references/advanced-patterns.md) — configuration dependency graph, crawl trade-off deep dives, recent AWS Glue features.
- [references/error-handling.md](references/error-handling.md) — crawler failure deep dives: AccessDenied, wrong schema, missing partitions, JDBC connect, no tables.

## Domain

AWS CloudOps / AWS Glue Crawler Schema Discovery & Data Catalog
Management.

## AWS documentation

- **Glue Crawler Guide** — https://docs.aws.amazon.com/glue/latest/dg/add-crawler.html
- **Classifiers** — https://docs.aws.amazon.com/glue/latest/dg/custom-classifier.html
- **Partition Projection** — https://docs.aws.amazon.com/athena/latest/ug/partition-projection.html
- **Lake Formation Integration** — https://docs.aws.amazon.com/lake-formation/latest/dg/how-data-lake-tasks-work.html
- **DynamoDB Export** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DataExport.html
- **JDBC Connections** — https://docs.aws.amazon.com/glue/latest/dg/connection-properties.html
- **Incremental Crawl** — https://docs.aws.amazon.com/glue/latest/dg/crawler-mappings-changes.html
- **Crawler Scheduling** — https://docs.aws.amazon.com/glue/latest/dg/schedule-a-crawler.html
