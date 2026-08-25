# Advanced Patterns — Redshift Serverless Deployer

2024-2026 Redshift Serverless feature changes moved verbatim from SKILL.md. Loaded on demand.

## Latest Redshift Serverless features (2024-2026)

- **Cross-Region snapshot copy (2024-2025):** automated snapshot copy
  to a secondary Region for disaster recovery. Requires a separate
  destination-Region KMS key and a snapshot copy grant. RPO is the
  snapshot interval (default 8 hours).
- **Cost controls with usage thresholds (2024-2025):** usage limits
  with `breach-action` of `log`, `emit-metric`, or `disable`. Pair
  with CloudWatch alarms on `ServerlessComputeCapacity` for proactive
  budget alerts.
- **AWS Secrets Manager integration (2024-2025):** admin password
  stored and rotated in Secrets Manager via managed rotation Lambda.
  Removes the need for manual rotation scripts.
- **Zero-ETL integrations (2024-2026):** near-real-time replication
  from Aurora PostgreSQL, RDS for PostgreSQL, and DynamoDB into
  Redshift Serverless without COPY/UNLOAD pipelines. Configured at
  the source database, not the namespace.
- **Concurrent scaling (2024-2025):** auto-scaling beyond base RPU for
  bursty workloads. Billed separately; pair with usage limits.
- **Query editor v2 enhancements (2024-2025):** schema visualizer,
  query history, saved queries, and chart exports.
- **ML-driven workload management (2024-2025):** automatic WLM queue
  tuning based on query patterns. No manual queue configuration.
- **Row-level security (2024-2026):** policy-based row filtering
  without view rewriting. Useful for multi-tenant analytics.
