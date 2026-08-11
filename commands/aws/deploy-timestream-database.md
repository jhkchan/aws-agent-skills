---
description: Provision an Amazon Timestream database and table with production-grade defaults (database creation, table creation, retention properties with memory store TTL vs magnetic store TTL, magnetic store write properties with S3 integration, partition key enforcement, scheduled query creation with SNS notification, batch load task, IAM policies, CloudWatch metrics). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create timestream database"
  - "deploy timestream database"
  - "create timestream table"
  - "timestream retention properties"
  - "timestream memory store ttl"
  - "timestream magnetic store ttl"
  - "timestream scheduled query"
  - "timestream magnetic store write"
  - "timestream partition key"
  - "timestream batch load"
  - "timestream s3 object store"
  - "timestream"
routes_to: timestream-database-deployer
---

# /aws:deploy-timestream-database

Activate the `timestream-database-deployer` skill and provision an
Amazon Timestream database and table with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Database creation (create-database) with optional KMS encryption
2. Table creation with retention properties (memory store TTL vs
   magnetic store TTL)
3. Magnetic store write properties (enable writes with S3 destination
   and bucket policy)
4. Partition key enforcement (REQUIRED vs OPTIONAL)
5. Scheduled query creation (notification config, target table, error
   reporting)
6. Query API patterns (raw queries vs scheduled query materialized
   views)
7. CloudWatch metrics (CUMULATIVE metering vs interval)
8. Magnetic store S3 bucket integration
9. Batch load task for bulk historical ingestion
10. IAM policies for Timestream resource types
11. Tagging for cost allocation
12. Recent features (2023-2026)

## When to use

- You need to create a Timestream database or table.
- You are configuring retention TTLs (memory store and magnetic
  store).
- You need to enable magnetic store writes for late-arrival data.
- You are setting up scheduled queries for materialized views.
- You need partition key enforcement for high-cardinality tables.
- You need to bulk-load historical data via batch load task.
- You need IAM policies for Timestream resource types.

## When NOT to use

- **DynamoDB** — use DynamoDB deployer skills.
- **Aurora/RDS** — use RDS deployer skills.
- **OpenSearch** — use OpenSearch deployer skills.
- **General S3 bucket provisioning** — use S3 bucket deployer skills.
- **Auditing existing Timestream tables** — use database audit skills.

## How to invoke

### Slash command

```
/aws:deploy-timestream-database
```

Then provide: database name, table name, memory store TTL, magnetic
store TTL, magnetic store write properties (S3 bucket), partition key
enforcement, scheduled query configuration (name, query, schedule,
target table, SNS topic, execution role), batch load task
configuration (data source bucket, report bucket), KMS key (if
custom), tags.

### Natural language

Any of these routes to the same skill:

- "create a timestream database for iot sensor data"
- "set up a timestream table with 12 hour memory store ttl"
- "enable magnetic store writes for late arrival data"
- "create a scheduled query for hourly aggregation"
- "configure partition key enforcement on my timestream table"

### CLI routing

```bash
node cli/bin/cli.js route "create a timestream database"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Timestream
resources. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-timestream-database

     Create a Timestream database IoTSensorData with table
     TemperatureReadings. Memory store TTL 12 hours, magnetic
     store TTL 365 days. Enable magnetic store writes with S3
     bucket timestream-magnetic-late-arrival. Create a scheduled
     query for hourly aggregation targeting HourlyTempAggregates.

Skill:
  TIMESTREAM: IoTSensorData / TemperatureReadings
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Database: IoTSensorData (region us-east-1)
    [✓] Table: TemperatureReadings
    [✓] Memory store TTL: 12h
    [✓] Magnetic store TTL: 365d
    [✓] Magnetic store writes: Enabled (S3: timestream-magnetic-late-arrival)
    [✓] Scheduled query: HourlyTemperatureAggregation
  VERIFICATION_COMMANDS:
    aws timestream-write describe-database --database-name IoTSensorData --region us-east-1
    aws timestream-write describe-table --database-name IoTSensorData --table-name TemperatureReadings --region us-east-1
```

## References

- Skill definition: `skills/timestream-database-deployer/SKILL.md`
- Retention and scheduled queries guide: `skills/timestream-database-deployer/references/retention-and-scheduled-queries.md`
- IAM and magnetic store guide: `skills/timestream-database-deployer/references/iam-and-magnetic-store.md`
- Eval suite: `skills/timestream-database-deployer/evals/evals.json`
