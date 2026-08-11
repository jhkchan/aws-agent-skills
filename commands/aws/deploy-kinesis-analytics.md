---
description: Provision a production-grade Amazon Kinesis Data Analytics application (Managed Service for Apache Flink, SQL, or Studio notebook) with checkpointing, parallelism, source/destination, and application snapshots.
nl_triggers:
  - "create kinesis data analytics"
  - "provision kinesis data analytics"
  - "deploy kinesis analytics"
  - "managed service for apache flink"
  - "kinesis analytics flink application"
  - "kinesis analytics sql application"
  - "kinesis analytics studio notebook"
  - "kinesis analytics checkpointing"
  - "kinesis analytics parallelism"
  - "kinesis analytics session windows"
  - "kinesis analytics zeppelin"
  - "kinesis analytics application snapshots"
  - "deploy flink streaming"
  - "deploy streaming sql"
routes_to: kinesis-analytics-deployer
---

# /aws:deploy-kinesis-analytics

Activate the `kinesis-analytics-deployer` skill and produce a
deployment plan for a production-grade Amazon Kinesis Data Analytics
application (Managed Service for Apache Flink, SQL, or Studio
notebook).

## What it does

Reads a deployment specification (runtime environment, service
execution role, source stream, destination, application code,
checkpointing, parallelism, CloudWatch logging, application
snapshots, Studio notebook configuration) and produces an ordered
deployment plan with:

1. Application-first ordering — the application is the container
   for all Flink/SQL streaming code. Without it, no code can run.
2. Service execution role gate — validates that an IAM role
   trusting `kinesisanalytics.amazonaws.com` exists with scoped
   Kinesis, Firehose, S3, and CloudWatch permissions. NEVER
   `AdministratorAccess`.
3. Source configuration — Kinesis Data Stream or Firehose with
   stream ARN and starting position (LATEST, TRIM_HORIZON, NOW).
4. Destination configuration — Kinesis Data Stream, Firehose, or
   S3 for processed record output.
5. Application code — Flink JAR/Python package in S3 (pinned to a
   versioned key) or inline SQL for SQL applications.
6. Checkpointing — interval and min-pause tuning for stateful
   Flink recovery.
7. Parallelism — parallelism and parallelismPerKPU tuning matched
   to the source shard count.
8. CloudWatch logging — log group and retention for application
   observability.
9. Application snapshots — user-triggered snapshots for planned
   stop/start and code updates with state preservation.
10. Studio notebooks (optional) — Apache Zeppelin runtime for
    interactive streaming analysis with Glue Data Catalog
    integration and deploy-as-application promotion.
11. Verification — post-deployment describe commands for all
    resources.

Emits a deterministic deployment plan per application:

```text
APPLICATION: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [x] Runtime environment selected (FLINK / SQL / Zeppelin)
  [x] Service execution role scoped (Kinesis, Firehose, S3, CloudWatch)
  [x] Source stream configured (Kinesis Data Stream, starting position)
  [x] Destination configured (Kinesis Data Stream, Firehose, S3)
  [x] Checkpointing tuned (interval, min pause)
  [x] Parallelism matched to source shards
  ...
VERIFICATION_COMMANDS:
  <ordered list of aws kinesisanalyticsv2 commands>
```

## When to invoke

Provide a deployment spec and ask any of:

- "create a Kinesis Data Analytics Flink application"
- "deploy a streaming SQL pipeline with session windows"
- "configure a Studio notebook with Zeppelin"
- "set up checkpointing for my Flink app"
- "tune parallelism for my KDA application"
- "create application snapshots for stateful recovery"

A bare application name + runtime + "deploy KDA" also routes here
via the orchestrator.

## Inputs

- **Required:** application_name, runtime_environment (FLINK-1_19,
  SQL-1_0, or ZEPPELIN-FLINK-1_0), service_execution_role_arn,
  source_stream_arn (Kinesis or Firehose).
- **Recommended:** destination_resource_arn, application_code (S3
  key for Flink, inline SQL for SQL apps), checkpoint_interval_ms,
  parallelism, parallelism_per_kpu, cloudwatch_log_group.
- **Optional:** application_snapshots_enabled, studio_notebook_glue_catalog,
  deploy_as_application, vpc_subnets, security_groups (for private
  sources like MSK), tags.

## Outputs

- One VERDICT block per application (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- CHECKLIST with all deployment dimensions validated.
- VERIFICATION_COMMANDS with ordered
  `aws kinesisanalyticsv2`, `aws iam`, `aws kinesis`, and
  `aws logs` commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 1 Deploy specialist for Kinesis Data Analytics).
- `/aws:audit-kinesis-stream` for post-deployment auditing of the
  source Kinesis Data Stream.
- `/aws:troubleshoot-kinesis-firehose` for Firehose delivery stream
  troubleshooting (related but separate service).
