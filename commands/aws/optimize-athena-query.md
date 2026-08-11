---
allowed-tools: Read, Bash, Grep
description: "Optimize Amazon Athena query performance and cost — file format migration (CSV to Parquet), partitioning, partition projection, compression, query rewriting, CTAS materialization, workgroup settings, and cost estimation ($5/TB scanned)"
nl_triggers:
  - "optimize Athena query"
  - "Athena query slow"
  - "Athena cost reduction"
  - "Athena partition projection"
  - "Athena file format Parquet"
  - "Athena CTAS optimization"
  - "Athena data scanned limit"
  - "Athena workgroup settings"
  - "Athena SELECT * optimization"
  - "Athena $5/TB scanned"
  - "Athena result reuse"
  - "Athena federated query"
  - "reduce Athena spend"
  - "Athena query timeout"
  - "Athena bucketing"
  - "Athena Parquet migration"
routes_to: athena-query-optimizer
---

# /aws:optimize-athena-query

Activate the `athena-query-optimizer` skill and optimize Athena query
performance and cost using the layered analysis framework.

## What it does

Reads a table's DDL, query history, and workgroup configuration, then
applies the ordered optimization logic:

1. **File format** — CSV/JSON to Parquet + Snappy (10-100x faster, 50-90%
   less data scanned). Highest-leverage single change.
2. **Partitioning** — unpartitioned to date/time partitioned. Partitioned
   table with >100K partitions to partition projection.
3. **Compression** — GZIP to Snappy (faster decompression) or ZSTD for
   large datasets.
4. **Query rewriting** — SELECT * to specific columns; add partition
   column WHERE filters; COUNT(DISTINCT) to APPROX_COUNT_DISTINCT.
5. **CTAS** — materialize repeated aggregations into curated tables.
6. **Workgroup** — set data-scanned limits, query timeout, result reuse.
7. **Bucketing** — for large-table JOINs on common keys.

Emits a deterministic optimization block per table or query:

```text
TARGET: <database/table | query-id | workgroup>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <recommendation and supporting data>
RECOMMENDATION:
  Current: <file format | partitioning | query pattern | workgroup config>
  Proposed: <file format | partitioning | query pattern | workgroup config>
  File format: <CSV | JSON | Parquet | ORC>
  Compression: <none | GZIP | Snappy | ZSTD>
  Partitioning: <none | date column | partition projection>
  Query rewrite: <avoid SELECT * | add partition filter | APPROXIMATE | none>
  Workgroup: <data scanned limit | query timeout | result reuse>
  CTAS: <materialization target | none>
  Confidence: <HIGH/MEDIUM/LOW>
ESTIMATED_SAVINGS:
  Cost (monthly): $<amount>
  Performance: <current runtime> → <proposed runtime>
  Data scanned per query: <current> → <proposed>
  Annual total: $<amount>
MIGRATION_STEPS:
  1. <action with DDL or CLI command>
  2. <verification step>
```

## When to invoke

Paste a table configuration + query history and ask any of:

- "this Athena query is too slow"
- "reduce our Athena spend"
- "should we use Parquet instead of CSV?"
- "set up partition projection"
- "optimize this SELECT * query"
- "materialize this aggregation via CTAS"
- "set a data-scanned limit on the workgroup"

A bare database/table name + any optimization verb also routes here.

## Inputs

- Table metadata: database name, table name, file format (CSV/JSON/Parquet/
  ORC), compression, partition columns, partition count.
- Query history: data scanned per query, runtime, frequency.
- Workgroup configuration: data-scanned limit, engine version, enforce
  setting, result reuse.
- S3 data layout: bucket/prefix, file sizes, partition structure.

## Outputs

- One optimization block per table, query pattern, or workgroup.
- Confidence level with rationale.
- Estimated monthly and annual cost savings with data-scan reduction.
- Specific DDL and CLI commands for migration.
- Row-count verification step before decommissioning source tables.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for Athena Analytics).
- `/aws:audit-athena-workgroup` for workgroup security and configuration
  audits.
- `/aws:optimize-s3-lifecycle` for S3 storage cost optimization (complements
  Athena scan-cost reduction).
