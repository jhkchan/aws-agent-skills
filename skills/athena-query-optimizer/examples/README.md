# Example usage: athena-query-optimizer

A walkthrough showing the skill optimizing a CSV table by migrating to
Parquet + Snappy with partitioning and a workgroup data-scanned limit,
demonstrating the layered optimization framework and cost estimation.

## Input (user prompt)

> Our Athena table `analytics_db.events` is CSV format, 1.2 TB. Every query
> scans the full table taking 320s and costing $6 each. We run ~220
> queries/day. There's no workgroup limit set. Help me optimize.

```text
Database: analytics_db
Table: events
Region: us-east-1

Table DDL: CSV, unpartitioned, no compression, 42 columns
Location: s3://data-lake/events/
Top queries: filter by event_time date range
Workgroup: no data-scanned limit, enforce=false, engine v3
Average queries/day: 220 (all scanning 1.2 TB)
```

## Skill output

```text
TARGET: analytics_db.events
VERDICT: OPPORTUNITY_FOUND
REASON: Table is unpartitioned CSV (1.2 TB). Top 10 queries scan the full
  table averaging 320s runtime. Migrating to Parquet + partitioning by date
  reduces average scan from 1.2 TB to 18 GB (daily queries). Adding a 10 GB
  data-scanned limit prevents runaway scans.
RECOMMENDATION:
  Current: CSV, unpartitioned, no compression, no workgroup limit
  Proposed: Parquet + Snappy, partitioned by dt, 10 GB workgroup limit
  File format: CSV → Parquet
  Compression: none → Snappy
  Partitioning: none → partitioned_by = ['dt']
  Query rewrite: SELECT * → SELECT 8 of 42 columns; add WHERE dt filter
  Workgroup: no limit → 10 GB data scanned per query
  CTAS: materialize daily_summary aggregation table
  Confidence: HIGH — DDL confirms CSV/unpartitioned, query history shows
    daily date-filtered queries scanning 1.2 TB each.
ESTIMATED_SAVINGS:
  Cost (monthly): $3,280.50 → $49.10
  Performance: 320s avg → 8s avg (40x faster)
  Data scanned per query: 1.2 TB → 18 GB (98.5% reduction)
  Annual total: $38,774.40
MIGRATION_STEPS:
  1. Create the Parquet partitioned table via CTAS:
     CREATE TABLE analytics_db.events_parquet
     WITH (format='PARQUET', parquet_compression='SNAPPY',
           partitioned_by=ARRAY['dt'],
           external_location='s3://data-lake/events/parquet/')
     AS SELECT event_id, user_id, event_type, amount, device, country,
       ip_address, session_id, event_time,
       date_format(event_time, '%Y-%m-%d') AS dt
     FROM analytics_db.events;
  2. Verify row count parity:
     SELECT COUNT(*) FROM analytics_db.events_parquet;
     SELECT COUNT(*) FROM analytics_db.events;
  3. Update downstream queries to use the new table + partition filter.
  4. Set the workgroup data-scanned limit:
     aws athena update-work-group --work-group primary \
       --configuration '{"BytesScannedCutoffPerQuery":10737418240,...}'
  5. Monitor query performance for 7 days before decommissioning the CSV table.
CONFIRM: Before running the CTAS (scans 1.2 TB, cost ~$6.00), emit and await:
  "CONFIRM: About to run CTAS migration on analytics_db.events (1.2 TB,
   estimated cost $6.00). Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **File format as Step 1.** A generic assistant may suggest "add partition
   columns" or "rewrite your queries" first. The skill recognizes that
   converting CSV to Parquet is the highest-leverage single change — 10-100x
   speedup before any other optimization.

2. **Layered cost estimation.** The skill stacks three savings layers:
   Parquet columnar pruning (42 columns → 8 read), Snappy compression
   (~60% additional reduction), and date partitioning (1/30th scan for
   daily queries). The combined estimate is 98.5% data scan reduction.

3. **Workgroup limit as a safety net.** The skill recommends setting a
   10 GB data-scanned limit to cap any future query at $0.05. A generic
   assistant rarely addresses the workgroup configuration.

4. **CTAS migration with row-count verification.** The skill specifies
   verifying row count parity before decommissioning the source table,
   preventing data loss.

5. **CONFIRM gate for the CTAS itself.** The CTAS costs ~$6.00 to run
   (scans 1.2 TB). The skill emits a CONFIRM gate before executing.

## Slash-command invocation

```
/aws:optimize-athena-query
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our Athena events table, it's CSV and every query costs $6"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: athena-query-optimizer]` and hands off
to this skill for the optimization block.

## Live-account follow-up (requires AWS CLI)

After remediating, validate the new table's query performance:

```bash
# Run a test query on the new Parquet table:
aws athena start-query-execution \
  --query-string "SELECT event_type, COUNT(*) FROM analytics_db.events_parquet
    WHERE dt >= '2026-07-01' GROUP BY event_type" \
  --work-group primary \
  --result-configuration OutputLocation=s3://data-lake/results/ \
  --query 'QueryExecutionId'

# Check the data scanned and runtime:
aws athena get-query-execution --query-execution-id <id> \
  --query 'QueryExecution.{Scanned:Statistics.DataScannedInBytes,
    Runtime:Statistics.EngineExecutionTimeInMillis,State:Status.State}'

# Monitor Athena spend trend:
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Athena"]}}'
```

If data scanned per query does not drop by >90% within 7 days, verify the
partition filter is present in all downstream queries.
