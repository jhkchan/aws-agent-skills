---
description: Provision an Amazon S3 table bucket with Apache Iceberg tables, namespace management, schema and partition spec, table maintenance (compaction, snapshot management, unreferenced file cleanup), table bucket policy (separate from regular S3 bucket policy), Athena integration via Iceberg REST catalog, and Lake Formation permissions. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create s3 table bucket"
  - "deploy s3 table bucket"
  - "s3 tables"
  - "s3 table bucket"
  - "iceberg table s3"
  - "s3 tables namespace"
  - "s3 table maintenance"
  - "s3 table compaction"
  - "s3 table bucket policy"
  - "iceberg rest catalog"
  - "athena s3 tables"
  - "lake formation s3 tables"
  - "apache iceberg table"
routes_to: s3-table-bucket-deployer
---

# /aws:deploy-s3-table-bucket

Activate the `s3-table-bucket-deployer` skill and provision an Amazon
S3 table bucket with Apache Iceberg tables and production-grade
defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Table bucket creation (purpose-built for tabular data)
2. Namespace management (required before table creation)
3. Table creation (Apache Iceberg format with schema + partition spec)
4. Table schema design (Iceberg column types, partition transforms)
5. Table maintenance (compaction, snapshot management, file cleanup)
6. Table bucket policy (SEPARATE from regular S3 bucket policy)
7. Iceberg REST catalog + Athena integration
8. Lake Formation integration (fine-grained access control)
9. Table format version (Iceberg v2 for row-level operations)
10. Partitioning strategy (aligned with query patterns)

## When to use

- You need to create an S3 table bucket for Apache Iceberg tables.
- You are managing namespaces within a table bucket.
- You are creating an Iceberg table in S3 Tables with schema and
  partition spec.
- You need to configure table maintenance (compaction, snapshot
  management, unreferenced file cleanup).
- You need to apply a table bucket policy (separate from S3 bucket
  policy).
- You need Athena integration via the Iceberg REST catalog.
- You need Lake Formation permissions on S3 Tables resources.

## When NOT to use

- **Regular S3 bucket operations** — use standard S3 bucket skills for
  general-purpose object storage.
- **S3 Glacier** — different storage class, not tabular data.
- **DynamoDB** — NoSQL managed database, not S3 Tables.
- **Redshift** — use Redshift skills for data warehouse provisioning.
- **Self-managed Iceberg on S3** — this skill covers S3 Tables (the
  managed service), not DIY Iceberg on regular S3.

## How to invoke

### Slash command

```
/aws:deploy-s3-table-bucket
```

Then provide: table bucket name, namespace name, table name, schema
(columns and types), partition spec, Iceberg format version,
maintenance configuration, table bucket policy (if needed), Athena
integration requirements, Lake Formation requirements, tags.

### Natural language

Any of these routes to the same skill:

- "create an S3 table bucket for analytics"
- "create an Iceberg table in S3 Tables"
- "configure S3 table maintenance compaction"
- "set up Athena with S3 Tables via REST catalog"
- "apply a table bucket policy for cross-account access"

### CLI routing

```bash
node cli/bin/cli.js route "create an s3 table bucket"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create S3 Tables
resources. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-s3-table-bucket

     Create an S3 table bucket named analytics-tables in us-east-1.
     Create namespace sales_analytics. Create an Iceberg v2 table
     named orders with columns: order_id (long), customer_id (long),
     order_date (timestamp), amount (double), status (string).
     Partition by day(order_date). Keep default maintenance.
     Tags: Environment=production, Team=analytics.

Skill:
  S3_TABLES: analytics-tables / sales_analytics / orders
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Table bucket: analytics-tables
    [✓] Namespace: sales_analytics
    [✓] Table: orders (ICEBERG v2)
    [✓] Schema: 5 columns
    [✓] Partition spec: day(order_date)
    [✓] Maintenance — compaction: ENABLED
    [✓] Maintenance — snapshot management: ENABLED
    [✓] Maintenance — file cleanup: ENABLED
  VERIFICATION_COMMANDS:
    aws s3tables get-table --table-bucket-arn <arn> --namespace sales_analytics --name orders --region us-east-1
```

## References

- Skill definition: `skills/s3-table-bucket-deployer/SKILL.md`
- Maintenance and Iceberg guide: `skills/s3-table-bucket-deployer/references/maintenance-and-iceberg.md`
- Policy and integrations guide: `skills/s3-table-bucket-deployer/references/table-bucket-policy-and-integrations.md`
- Eval suite: `skills/s3-table-bucket-deployer/evals/evals.json`
