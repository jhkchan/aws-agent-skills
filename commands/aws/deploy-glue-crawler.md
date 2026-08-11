---
description: Provision an AWS Glue Crawler with production-grade defaults (data source selection for S3/DynamoDB/JDBC, IAM role with least-privilege permissions, classifier configuration with correct ordering, schema merge policy, partitioning strategy with partition projection, Lake Formation integration, catalog database target, scheduling with cron or event-driven S3 Event Notifications, incremental vs full crawl, schema evolution handling). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create glue crawler"
  - "deploy glue crawler"
  - "glue crawler classifier"
  - "glue crawler schedule"
  - "glue crawler lake formation"
  - "glue crawler partition projection"
  - "glue dynamodb crawler"
  - "glue jdbc crawler"
  - "glue crawler s3"
  - "glue schema discovery"
  - "crawl s3 data"
  - "discover glue schema"
  - "glue crawler incremental"
routes_to: glue-crawler-deployer
---

# /aws:deploy-glue-crawler

Activate the `glue-crawler-deployer` skill and provision an AWS Glue
Crawler with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Data source selection (S3, DynamoDB export, JDBC)
2. IAM role with least-privilege permissions
3. Classifier configuration (Grok, JSON, CSV — first match wins)
4. Schema merge policy (MergeNewColumns, UpdateAll)
5. Partitioning strategy (folder vs partition projection)
6. Lake Formation integration (LF permissions, LF-tags)
7. Catalog database target
8. Scheduling (cron vs event-driven via S3 Event Notifications)
9. Incremental vs full crawl trade-off
10. Schema evolution handling
11. Output table configuration (prefix, threshold)
12. Recent features (incremental improvements, open table format support)

## When to use

- You need to create a Glue Crawler for S3 data.
- You are setting up a DynamoDB export crawl.
- You need a JDBC crawler with a Glue Connection.
- You want to configure custom classifiers (Grok, JSON, CSV).
- You need partition projection for cost reduction.
- You are integrating with Lake Formation.
- You want event-driven crawl via S3 Event Notifications.

## When NOT to use

- **Glue ETL jobs** — use glue-job-troubleshooter for ETL job issues.
- **Glue DataBrew** — different service for data preparation.
- **Auditing existing crawlers** — use glue-crawler-job-auditor.
- **Athena workgroup management** — use athena-workgroup-auditor.

## How to invoke

### Slash command

```
/aws:deploy-glue-crawler
```

Then provide: data source (S3 path, DynamoDB table, JDBC connection),
IAM role name, classifier names (if custom), database name, schedule
type, crawl mode (incremental/full), partition strategy, Lake
Formation (if applicable), table prefix, tags.

### Natural language

Any of these routes to the same skill:

- "create a Glue Crawler for my S3 data"
- "set up a JDBC crawler for PostgreSQL"
- "configure a DynamoDB export crawl"
- "create a custom Grok classifier for log parsing"
- "enable partition projection on my events table"

### CLI routing

```bash
node cli/bin/cli.js route "create a glue crawler"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or
configure Glue Crawlers. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-glue-crawler

     Create a Glue Crawler for S3 data at
     s3://my-data-lake/events/year=2026/. JSON files. Custom JSON
     classifier EventsJsonClassifier. Partition projection for
     year/month/day. Database analytics_db. Incremental crawl.
     Daily at 2 AM UTC. Table prefix raw_.

Skill:
  GLUE_CRAWLER: events-crawler
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Classifiers: ["EventsJsonClassifier"] (first-match-wins)
    [✓] Partitioning: partition-projection (year, month, day)
    [✓] Crawl mode: incremental
    [✓] Schedule: cron(0 2 * * ? *)
  VERIFICATION_COMMANDS:
    aws glue get-crawler --name events-crawler
    aws glue get-table --database-name analytics_db --name raw_events
```

## References

- Skill definition: `skills/glue-crawler-deployer/SKILL.md`
- Classifiers and partitioning guide: `skills/glue-crawler-deployer/references/classifiers-and-partitioning.md`
- IAM and Lake Formation guide: `skills/glue-crawler-deployer/references/iam-and-lake-formation.md`
- Eval suite: `skills/glue-crawler-deployer/evals/evals.json`
