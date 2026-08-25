# Advanced Patterns — Athena Query Optimizer

Load-on-demand deep dives moved verbatim from SKILL.md: consolidated expert heuristics and recent AWS features.

## Expert heuristic — consolidated (non-obvious Athena behaviours)

| Heuristic | Impact on recommendation |
|---|---|
| Athena charges per byte read, not per compute second | Reducing data scanned is the ONLY cost lever. |
| Parquet columnar pruning reads only selected columns | SELECT * on 50-column Parquet reads 50 columns; SELECT 3 reads 3. |
| Partition pruning happens at the S3 listing level | Queries without a partition-column WHERE clause scan every partition. |
| Partition projection eliminates Glue metadata latency | Essential for 100K+ partition tables; removes MSCK REPAIR need. |
| Snappy beats GZIP for query speed | GZIP decompression is CPU-bound; Snappy is 2-3x faster to decompress. |
| APPROX_COUNT_DISTINCT is 10-50x faster than COUNT(DISTINCT) | Error is < 3% with default settings; acceptable for dashboards. |
| CTAS breaks even proportional to query frequency | Materialize if the same aggregation runs 10+ times/day. |
| Workgroup data-scanned limits prevent the $5,000 SELECT * | Set limits conservatively; users get a clear error message. |
| Athena engine v3 enables dynamic partition pruning | The engine prunes partitions at runtime based on JOIN conditions. |
| Result reuse caches identical query output | Enable for dashboard workloads; 0 cost for cache hits. |
| Federated queries are NOT $5/TB | They use connector-specific pricing (Lambda + source system cost). |
| Small files (< 8 MB) cause S3 request overhead | Consolidate to 100 MB - 1 GB files per partition. |

## Recent AWS features (2024-2026)

- **Athena query result reuse (2023-2024 GA):** Caches identical query
  results for a configurable TTL. Cache hits cost $0 and return in
  milliseconds. Enable via workgroup configuration:
  `Configuration.ResultConfiguration.ResultReuseConfiguration`.
- **Athena federated queries (2023-2025):** Query non-S3 data sources
  (DynamoDB, RDS, Redshift) via Lambda connectors. Not priced at $5/TB —
  cost is Lambda invocation + source system charges. Use for cross-source
  JOINs without ETL.
- **Athena Spark notebook integration (2024-2025):** Run interactive Spark
  sessions within Athena for complex transformations. Priced per DPU-hour
  ($0.35/DPU-hour). Use when SQL is insufficient for the transformation.
- **Athena engine version 3 (2022+, continuously updated 2024-2026):**
  Dynamic partition pruning (runtime partition elimination based on JOIN
  conditions), improved JOIN performance, subquery materialization. Ensure
  workgroup uses engine v3.
- **Apache Iceberg table support (2023-2025):** Athena can read and write
  Iceberg tables with time travel, schema evolution, and hidden partitioning.
  Iceberg on Athena enables ACID transactions and partition evolution
  without re-creating tables.
- **Athena parameterized queries (2024-2025):** Pre-compiled query templates
  that accept parameters. Improves security (SQL injection prevention) and
  enables result reuse for parameterized queries.
