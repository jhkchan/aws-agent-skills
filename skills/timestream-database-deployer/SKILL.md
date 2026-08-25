---
name: timestream-database-deployer
description: 'Provisions Amazon Timestream databases and tables with production defaults: database creation (create-database), table creation (create-table) with retention properties (memory store TTL vs magnetic store TTL), magnetic store write properties (enable writes with S3 destination), partition key enforcement, scheduled query creation (notification config, target SNS/SQS, error reporting), CloudWatch metrics (CUMULATIVE metering vs interval), query API (raw vs scheduled), magnetic store S3 bucket integration, tagging, IAM policies for Timestream (database/table/scheduled query resource types), and batch load task. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Timestream database or table, configuring retention TTLs. Triggers: create timestream database, create timestream table, timestream retention properties, timestream memory store TTL, timestream magnetic store TTL, timestream scheduled query, timestream magnetic store write, timestream partition key, timestream batch load.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with timestream-write and timestream-query access. Works with Terraform aws_timestreamwrite_database / aws_timestreamwrite_table / aws_timestreamquery_scheduled_query resources and CloudFormation AWS::Timestream::Database / AWS::Timestream::Table / AWS::Timestream::ScheduledQuery templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, timestream, time-series, cloudops, deploy, databases, provisioning, retention, scheduled-query, magnetic-store, memory-store, partition-key
  dependencies: aws-orchestrator
  keywords: aws, timestream, time series, database, table, cloudops, deploy, provisioning, memory store, magnetic store, retention, scheduled query, partition key, batch load
  when_to_use: Invoke when the user wants to create an Amazon Timestream database or table, configure memory store and magnetic store retention TTLs, set up scheduled queries for materialized views, enable magnetic store write properties with S3 object store integration, configure partition key enforcement for query performance, create a batch load task for bulk ingestion, or deploy IAM policies for Timestream resource types. Do NOT invoke for DynamoDB (use DynamoDB skills), for Aurora/RDS (use RDS skills), or for general S3 bucket provisioning (use S3 skills).
---

# Timestream Database Deployer

An AWS CloudOps agent skill that provisions Amazon Timestream
databases and tables with correct defaults. The skill walks the
operator through database creation, table creation with retention
properties (memory store TTL vs magnetic store TTL), magnetic store
write properties (enable writes with S3 destination), partition key
enforcement, scheduled query creation (notification config, target
SNS/SQS, error reporting), CloudWatch metrics (CUMULATIVE metering vs
interval), query API (raw vs scheduled), magnetic store S3 bucket
integration, tagging, IAM policies for Timestream resource types
(database, table, scheduled query), and batch load task creation,
captures configuration decisions, explains why each default matters,
and emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

create Timestream database, create Timestream table, Timestream
retention properties, Timestream memory store TTL, Timestream magnetic
store TTL, Timestream scheduled query, Timestream magnetic store
write, Timestream partition key, Timestream batch load, Timestream
S3 object store.

## STRICT output contract

When this skill is invoked with a Timestream-provisioning request
(create a database, create a table, configure retention TTLs, set up
scheduled queries, enable magnetic store writes, configure partition
keys, create a batch load task, or a partial configuration), the agent
MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels
`TIMESTREAM:`, `VERDICT:`, `CHECKLIST:`, and
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
| Step 1 — Database creation | Core database resource |
| Step 2 — Table creation with retention properties | Memory/magnetic TTL |
| Step 3 — Magnetic store write properties (S3) | Late-arrival writes |
| Step 4 — Partition key enforcement | Query performance |
| Step 5 — Scheduled query creation | Materialized views |
| Step 6 — Query API (raw vs scheduled) | Query patterns |
| Step 7 — CloudWatch metrics (CUMULATIVE vs interval) | Monitoring & cost |
| Step 8 — Magnetic store S3 bucket integration | S3 object store |
| Step 9 — Batch load task | Bulk ingestion |
| Step 10 — IAM policies for Timestream | Access control |
| Step 11 — Tagging | Cost allocation |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/retention-and-scheduled-queries.md | TTL + scheduled query detail |
| references/iam-and-magnetic-store.md | IAM + magnetic store write detail |

## Mindset

**One-line takeaway:** Amazon Timestream is a purpose-built time-series
database with a two-tier storage model (memory store for recent data,
magnetic store for historical data). The memory store TTL controls how
long data stays in fast in-memory queries; the magnetic store TTL
controls how long data is retained in cost-effective magnetic storage.
Scheduled queries pre-compute materialized views for predictable query
patterns. Magnetic store write properties enable late-arrival data to
be written directly to the magnetic store via S3.

Three misconceptions dominate Timestream misdesign at provisioning
time:

- **"Memory store and magnetic store TTLs are interchangeable."** They
  are NOT. Memory store TTL (minutes to hours) determines how long data
  is queryable from fast in-memory storage at higher cost. Magnetic
  store TTL (days to years) determines long-term retention in cheaper
  storage. Data transitions from memory store to magnetic store
  automatically when the memory store TTL expires. Setting the memory
  store TTL too high inflates cost; setting it too low may push data to
  magnetic store before hot queries can access it at speed.

- **"Scheduled queries are just cached queries."** They are more than
  caches. Scheduled queries continuously pre-compute and materialize
  results into a target table, with an error reporting configuration
  (SNS/SQS notification) and a target configuration (destination
  table). They reduce query latency and cost for predictable, recurring
  aggregation patterns but require IAM permissions for BOTH the
  scheduled query resource AND the target table.

- **"Magnetic store writes are enabled by default."** They are NOT.
  By default, writes to the magnetic store are disabled. You must
  explicitly enable `MagneticStoreWriteProperties` with an S3 bucket
  destination to allow late-arrival data (data with timestamps older
  than the memory store TTL) to be ingested directly into the magnetic
  store via S3. Without this, late-arrival records are rejected.

## Configuration dependency graph (novel heuristic)

Timestream configurations are NOT independent. The database must exist
before tables can be created. The table must exist before scheduled
queries can target it. Magnetic store write properties require an S3
bucket with correct bucket policy. Scheduled queries require SNS/SQS
notification configuration. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Database | account has timestream:CreateDatabase permission | database name is immutable after creation; KMS key (if specified) cannot be changed | all tables within the database |
| Table | database exists; timestream:CreateTable permission | retention properties can be updated; magnetic store write properties require S3 bucket with bucket policy | data ingestion and queries |
| Retention properties (memory/magnetic TTL) | table exists | memory store TTL must be >= 1 minute; magnetic store TTL must be >= 1 day; updates take effect for new writes | data lifecycle and cost |
| Magnetic store write properties | table exists; S3 bucket exists with bucket policy granting Timestream write access | S3 bucket must have a bucket policy allowing `s3:PutObject` for `timestream-compute` principal; without it, writes silently fail | late-arrival data ingestion via S3 |
| Partition key enforcement | table exists; schema defined | partition key type is enforced at write time; mismatched records are rejected | query performance optimization |
| Scheduled query | target table exists; SNS/SQS topic exists for notifications; IAM role with query permissions | scheduled query runs on a schedule; errors reported to notification config; requires timestream:CreateScheduledQuery | pre-computed materialized views |
| Batch load task | table exists; S3 data source bucket with CSV/Parquet data; IAM role for batch load | batch load is asynchronous; task progresses through stages (PENDING, LOADING, SUCCEEDED, FAILED) | bulk historical data ingestion |
| IAM policy | resource ARNs for database, table, scheduled query | resource types: database, table, scheduled-query, batch-load-task | access control for all operations |
| Tagging | database or table exists | tags can be added/removed at any time; tag keys are case-sensitive | cost allocation and governance |

**The magnetic-store-write-properties row is the one a baseline model
misses.** Enabling magnetic store writes is a deliberate configuration
that requires an S3 bucket with a specific bucket policy. A baseline
model creates the table without magnetic store write properties and
does not flag that late-arrival data is silently rejected. The
procedure below forces an explicit decision on this configuration.

**Cross-dependency gotchas:**
- Database name is immutable. Choose carefully at creation time. The
  database ARN follows the pattern
  `arn:aws:timestream:<region>:<account>:database/<db-name>`.
- Table retention properties can be updated, but the memory store TTL
  must always be >= 1 minute and the magnetic store TTL must be >= 1
  day. Reducing TTLs does not delete data already in the magnetic
  store.
- Scheduled queries require a target table that already exists. The
  target table receives the materialized query results. The scheduled
  query itself is a separate resource with its own ARN.
- Magnetic store write properties S3 bucket must have a bucket policy
  granting `s3:PutObject` to the Timestream service principal. The
  bucket must be in the same region as the Timestream table.
- Batch load tasks are one-shot operations (not continuous). For
  ongoing bulk ingestion, use the regular WriteRecords API or
  magnetic store write properties.

## Expert heuristic: memory store TTL tuning for query performance vs cost trade-off

A baseline model says "set retention and move on." The correct
heuristic recognizes that memory store TTL directly impacts both query
latency and cost, and the optimal value depends on the workload's
hot-data window.

```text
Data ingestion timeline:
  t=0: record written → enters memory store
  t=memory_store_ttl: record transitions to magnetic store
  t=memory_store_ttl + magnetic_store_ttl: record is deleted

Query latency by storage tier:
  Memory store:     sub-second to low seconds (in-memory scan)
  Magnetic store:   seconds to tens of seconds (disk-based scan)

Cost by storage tier:
  Memory store:     higher (measured by memory store GB-hours)
  Magnetic store:   lower (measured by magnetic store GB-hours)

Tuning the memory store TTL:
  ├── Hot queries access data from last 15 min → memory store TTL = 15m
  │     cost: moderate (only 15 min of data in memory)
  │     latency: sub-second for recent data
  ├── Hot queries access data from last 12 hours → memory store TTL = 12h
  │     cost: higher (12 hours of data in memory)
  │     latency: sub-second for half-day window
  ├── Hot queries access data from last 7 days → memory store TTL = 7d?
  │     NO — use scheduled query instead (pre-aggregate hourly/daily)
  │     memory store TTL = 1h, scheduled query materializes 7-day aggregates
  │     cost: lower (memory store holds 1h; magnetic store holds aggregates)
  └── Historical analysis (months/years) → memory store TTL = 1h
        magnetic store TTL = 1y+, scheduled queries for common aggregations
```

**Key implication:** the memory store TTL is NOT just a retention
setting — it is a performance and cost lever. For workloads with a
predictable hot-data window, set the TTL to match that window. For
workloads needing long-range aggregations, use scheduled queries to
pre-compute materialized views rather than extending the memory store
TTL.



## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS region supports Timestream | Timestream is not available in all regions | `aws timestream-write list-databases --region <region>` |
| Database name chosen (if creating database) | Database name is immutable after creation | Confirm unique name; 3-256 chars, alphanumeric and underscore |
| Table name chosen (if creating table) | Table belongs to a database | Confirm database exists |
| Retention TTLs decided | Memory store TTL (min-hours) and magnetic store TTL (days-years) | Assess hot-data window and retention requirements |
| S3 bucket for magnetic store writes (if enabling) | Late-arrival data ingestion requires S3 destination with bucket policy | `aws s3api get-bucket-policy --bucket <bucket>` |
| SNS/SQS topic ARN for scheduled query notifications (if creating scheduled query) | Error reporting requires notification target | `aws sns list-topics` or `aws sqs list-queues` |
| IAM permissions for timestream-write and timestream-query | CreateDatabase, CreateTable, UpdateTable, CreateScheduledQuery | Verify IAM policy attached to caller |
| KMS key ARN (if using customer-managed encryption) | Timestream supports customer-managed KMS encryption at database level | `aws kms describe-key --key-id <key-id>` |
| Partition key schema decided (if enforcing) | Partition keys improve query performance for specific access patterns | Analyze query patterns for enforcement benefit |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Database creation

A Timestream database is the container for one or more tables. The
database name is immutable after creation.

create-database (+KMS, +tags), describe-database verify, naming rules, ARN pattern — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

## Step 2 — Table creation with retention properties

A Timestream table belongs to a database and stores time-series
records. Each table has its own retention properties: memory store
TTL and magnetic store TTL.

create-table with retention, retention min/max rules, update-table TTL change — moved verbatim.
Full detail: [Retention and scheduled queries](references/retention-and-scheduled-queries.md).

**Common mistake:** setting memory store TTL too high for a high-volume
ingestion table. Memory store charges are per GB-hour. A table
ingesting 100 GB/day with a 30-day memory store TTL retains 3000 GB
in memory store — extremely expensive. Use scheduled queries instead.

## Step 3 — Magnetic store write properties (S3)

By default, magnetic store writes are disabled. Late-arrival data
(records with timestamps older than the memory store TTL) is rejected.
Enabling magnetic store write properties routes late-arrival data to
an S3 bucket, which Timestream then ingests into the magnetic store.

bucket creation, bucket-policy JSON, update-table MagneticStoreWriteProperties — moved verbatim.
Full detail: [IAM and magnetic store](references/iam-and-magnetic-store.md).

## Step 4 — Partition key enforcement

Partition keys optimize query performance by restricting the data
scanned for specific access patterns. When a schema includes partition
key enforcement, records with mismatched partition key types are
rejected at write time.

create-table with CompositePartitionKey schema — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

**Partition key configuration options:**

| Option | Values | Effect |
|---|---|---|
| EnforcementInRecord | REQUIRED, OPTIONAL | REQUIRED rejects records without the partition key dimension; OPTIONAL allows records without it |
| DimInsightsOptimization | ENABLED, DISABLED | ENABLED optimizes partition key access for common dimension patterns |


**When to use partition key enforcement:**
- Queries frequently filter by specific dimensions (e.g., device_id,
  region, customer_id).
- The table has high cardinality across a few dimensions.
- You want to reject malformed records at write time.

## Step 5 — Scheduled query creation

Scheduled queries continuously pre-compute materialized results into a
target table. They reduce latency and cost for predictable, recurring
query patterns.

target table, SNS topic, create-scheduled-query, component table — moved verbatim.
Full detail: [Retention and scheduled queries](references/retention-and-scheduled-queries.md).

## Step 6 — Query API (raw vs scheduled)

Timestream supports two query patterns: raw queries (direct SQL
against source tables) and scheduled query results (queries against
materialized views in target tables).

raw SQL query, materialized-view query — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

**When to use each:**

| Pattern | Latency | Cost | Use case |
|---|---|---|---|
| Raw query | Higher (full scan) | Higher (scans more data) | Ad-hoc analysis, debugging |
| Scheduled query result | Lower (pre-computed) | Lower (scans less data) | Dashboards, recurring reports |

## Step 7 — CloudWatch metrics (CUMULATIVE vs interval)

Timestream publishes CloudWatch metrics in two metering modes:
CUMULATIVE (total since table creation) and interval (per-period
delta). Understanding the difference is critical for cost monitoring.

**Key Timestream CloudWatch metrics:**

| Metric | Metering | What it measures |
|---|---|---|
| MemoryStoreMeteredBytes | CUMULATIVE | Total bytes billed in memory store |
| MagneticStoreMeteredBytes | CUMULATIVE | Total bytes billed in magnetic store |
| SuccessRequestCount | Interval | Successful write requests per period |
| FailedRequestCount | Interval | Failed write requests per period |
| QueryBytesRead | Interval | Bytes scanned by queries per period |
| QueryRequestCount | Interval | Number of query requests per period |

MemoryStoreMeteredBytes (CUMULATIVE), QueryBytesRead (interval) — moved verbatim.
Full detail: [Diagnostic commands](references/diagnostic-commands.md).

**Critical:** CUMULATIVE metrics show the running total. To compute
per-period cost, subtract the previous period's value. Interval
metrics show the delta per period directly.

## Step 8 — Magnetic store S3 bucket integration

The magnetic store write properties S3 bucket serves two purposes:
late-arrival data ingestion and rejected data location. The bucket
must have a policy granting Timestream write access.

get-bucket-policy, describe-table MagneticStoreWriteProperties — moved verbatim.
Full detail: [Diagnostic commands](references/diagnostic-commands.md).

## Step 9 — Batch load task

Batch load tasks perform bulk ingestion of historical data from S3
(CSV or Parquet) into a Timestream table. Batch load is asynchronous
and progresses through stages.

create-batch-load-task, stage table, CSV format requirements — moved verbatim.
Full detail: [Advanced patterns](references/advanced-patterns.md).

## Step 10 — IAM policies for Timestream

Timestream uses several resource types for IAM policies: database,
table, scheduled query, and batch load task.

WriteRecords/Describe/Select policy JSON, ScheduledQueryExecutionRole trust policy JSON — moved verbatim.
Full detail: [IAM and magnetic store](references/iam-and-magnetic-store.md).

## Step 11 — Tagging

Tags enable cost allocation and governance for Timestream resources.

tag-resource, list-tags-for-resource — moved verbatim.
Full detail: [Worked examples](references/worked-examples.md).

## Step 12 — Recent features

partition keys, magnetic store writes, batch load, dim insights, Terraform — moved verbatim.
Full detail: [Advanced patterns](references/advanced-patterns.md).

## NEVER do these things

1. **NEVER set memory store TTL too high for high-volume tables.**
   Memory store charges are per GB-hour. A high-ingestion table with a
   long memory store TTL is extremely expensive. Use scheduled queries
   to pre-compute aggregates and keep the memory store TTL short.

2. **NEVER assume magnetic store writes are enabled by default.** By
   default, late-arrival data (timestamps older than the memory store
   TTL) is silently rejected. You MUST explicitly enable
   MagneticStoreWriteProperties with an S3 destination to accept
   late-arrival data.

3. **NEVER create a scheduled query without creating the target table
   first.** The scheduled query fails at execution time if the target
   table does not exist. The target table receives the materialized
   query results.

4. **NEVER forget the S3 bucket policy for magnetic store writes.**
   The S3 bucket must have a bucket policy granting `s3:PutObject` to
   the Timestream service principal. Without it, late-arrival writes
   silently fail even when magnetic store writes are enabled.

5. **NEVER use CUMULATIVE CloudWatch metrics as per-period values.**
   CUMULATIVE metrics (MemoryStoreMeteredBytes,
   MagneticStoreMeteredBytes) show the running total since table
   creation. To compute per-period cost, subtract the previous
   period's value.

6. **NEVER delete or modify S3 objects created by Timestream magnetic
   store writes.** These objects are managed by the Timestream service.
   Configuring S3 lifecycle rules to delete them corrupts the magnetic
   store ingestion pipeline.

7. **NEVER create a scheduled query without an error notification
   configuration.** Scheduled queries can fail silently (DDL errors,
   permission issues, schema mismatches). Configure an SNS topic or
   SQS queue for error reporting to catch failures early.

8. **NEVER assume the scheduled query execution role only needs query
   permissions.** The role requires permissions to query the source
   table, write to the target table, AND publish to the SNS/SQS
   notification target. Missing any of these causes silent failures.

9. **NEVER ignore partition key enforcement for high-cardinality
   tables.** If queries frequently filter by specific dimensions,
   partition key enforcement dramatically reduces scan volume and
   cost. Without it, queries scan the full table.

10. **NEVER assume batch load tasks are continuous.** Batch load is a
    one-shot bulk ingestion operation. For ongoing data ingestion, use
    the WriteRecords API or magnetic store write properties.

## Output format

```text
TIMESTREAM: <database-name> / <table-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Database: <database-name> (region <region>)
  [✓|✗] Table: <table-name>
  [✓|✗] Memory store TTL: <hours>h
  [✓|✗] Magnetic store TTL: <days>d
  [✓|✗] Magnetic store writes: Enabled (S3: <bucket>) | Disabled
  [✓|✗] Partition key enforcement: REQUIRED | OPTIONAL | None
  [✓|✗] Scheduled query: <name> (schedule: <expression>, target: <table>)
  [✓|✗] Scheduled query notification: SNS <topic-arn>
  [✓|✗] Scheduled query execution role: <role-arn>
  [✓|✗] Batch load task: <task-id> (status: <stage>) | None
  [✓|✗] KMS encryption: customer-managed (<key-arn>) | service-managed
  [✓|✗] IAM policy: database/table/scheduled-query resource ARNs
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws timestream-write describe-database --database-name <database-name> --region <region>
  aws timestream-write describe-table --database-name <database-name> --table-name <table-name> --region <region>
  aws timestream-query describe-scheduled-query --scheduled-query-arn <arn> --region <region>
```

### Worked example — database with table, scheduled query, and magnetic store writes

```text
TIMESTREAM: IoTSensorData / TemperatureReadings
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Database: IoTSensorData (region us-east-1)
  [✓] Table: TemperatureReadings
  [✓] Memory store TTL: 12h
  [✓] Magnetic store TTL: 365d
  [✓] Magnetic store writes: Enabled (S3: timestream-magnetic-late-arrival-us-east-1)
  [✓] Partition key enforcement: REQUIRED
  [✓] Scheduled query: HourlyTemperatureAggregation (schedule: rate(1 hour), target: HourlyTempAggregates)
  [✓] Scheduled query notification: SNS arn:aws:sns:us-east-1:123456789012:timestream-scheduled-query-errors
  [✓] Scheduled query execution role: arn:aws:iam::123456789012:role/TimestreamScheduledQueryRole
  [✓] Batch load task: None
  [✓] KMS encryption: service-managed
  [✓] IAM policy: database/table/scheduled-query resource ARNs configured
  [✓] Tags: Environment=production, Team=iot
VERIFICATION_COMMANDS:
  aws timestream-write describe-database --database-name IoTSensorData --region us-east-1
  aws timestream-write describe-table --database-name IoTSensorData --table-name TemperatureReadings --region us-east-1
  aws timestream-query describe-scheduled-query --scheduled-query-arn arn:aws:timestream:us-east-1:123456789012:scheduled-query/HourlyTemperatureAggregation --region us-east-1
```

## Error handling

table creation, magnetic store update, scheduled query failure, batch load stuck, late-arrival rejection, memory store cost — moved verbatim.
Full detail: [Error handling](references/error-handling.md).

## References (load on demand)

- [Retention and scheduled queries](references/retention-and-scheduled-queries.md) — TTL rules and updates, scheduled query creation, materialized-view freshness heuristic
- [IAM and magnetic store](references/iam-and-magnetic-store.md) — magnetic store bucket policy + setup, late-arrival heuristic, IAM and execution-role policy JSON
- [Worked examples](references/worked-examples.md) — database / table / partition-key / query / tagging CLI walkthroughs
- [Diagnostic commands](references/diagnostic-commands.md) — CloudWatch metering queries, magnetic store integration verification
- [Advanced patterns](references/advanced-patterns.md) — batch load task detail, recent features
- [Error handling](references/error-handling.md) — table creation, magnetic store updates, scheduled query failures, cost spikes

## Domain

AWS CloudOps / Amazon Timestream Time-Series Database Provisioning &
Data Lifecycle Management.

## AWS documentation

- **Timestream Developer Guide** — https://docs.aws.amazon.com/timestream/latest/developerguide/what-is-timestream.html
- **Create database** — https://docs.aws.amazon.com/timestream/latest/developerguide/API_CreateDatabase.html
- **Create table** — https://docs.aws.amazon.com/timestream/latest/developerguide/API_CreateTable.html
- **Retention properties** — https://docs.aws.amazon.com/timestream/latest/developerguide/data-lifecycle.html
- **Magnetic store writes** — https://docs.aws.amazon.com/timestream/latest/developerguide/magnetic-store-writes.html
- **Scheduled queries** — https://docs.aws.amazon.com/timestream/latest/developerguide/scheduled-queries.html
- **Batch load** — https://docs.aws.amazon.com/timestream/latest/developerguide/batch-load.html
- **Partition keys** — https://docs.aws.amazon.com/timestream/latest/developerguide/partition-keys.html
- **IAM policies** — https://docs.aws.amazon.com/timestream/latest/developerguide/security-iam.html
- **CloudWatch metrics** — https://docs.aws.amazon.com/timestream/latest/developerguide/monitoring-cloudwatch.html
