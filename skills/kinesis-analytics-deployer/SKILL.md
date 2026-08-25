---
name: kinesis-analytics-deployer
description: 'Deploys Amazon Kinesis Data Analytics applications (Managed Service for Apache Flink and Studio SQL) with production-grade config: application creation (runtime FLINK-1_19 or SQL-1_0, service execution role), source (Kinesis Data Stream or Firehose with stream ARN, starting position), destination (Kinesis Data Stream, Firehose, S3 with parallelism), SQL vs Flink selection, checkpointing (interval, min pause), parallelism and parallelismPerKPU tuning, CloudWatch logging, application snapshots for stateful recovery, Studio notebooks with Apache Zeppelin, session window SQL patterns, latest features (Studio notebooks, Zeppelin, session windows, snapshots, custom app code via S3). Emits a READY_TO_DEPLOY checklist. Use when creating a KDA application, deploying a Flink or SQL streaming job, validating config, or generating CLI/IaC templates. Triggers: Kinesis Data Analytics, Managed Flink, KDA Studio, Zeppelin, streaming SQL, Flink application, checkpointing, parallelism, session windows.'
license: Apache-2.0
compatibility: 'Requires an LLM agent runtime (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with kinesisanalytics, kinesisanalyticsv2, kinesis, firehose, iam, logs, and s3 access. Works with Terraform aws_kinesisanalyticsv2_application / aws_kinesis_analytics_application resources, CloudFormation AWS::KinesisAnalyticsV2::Application resources, and the AWS Console Kinesis Data Analytics wizard.'
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
  tags: aws, kinesis, kinesis-analytics, cloudops, deploy, analytics, streaming, flink
  dependencies: aws-orchestrator
  keywords: aws, kinesis, kinesis-analytics, kinesis-data-analytics, managed-flink, apache-flink, cloudops, deploy, analytics, streaming, flink, studio-notebook, zeppelin, checkpointing, parallelism, session-windows
  when_to_use: Invoke when the user wants to create a new Kinesis Data Analytics application (Managed Service for Apache Flink or Studio SQL), deploy a Flink streaming job, deploy a streaming SQL pipeline with session/hopping/tumbling windows, configure an interactive Studio notebook with Zeppelin, validate an existing KDA configuration against best practices, generate deployment CLI commands or IaC templates, or troubleshoot a KDA deployment failure caused by missing prerequisites (execution role, source stream, checkpoint configuration). Do NOT invoke for Kinesis Data Streams provisioning (use kinesis-stream-auditor), Kinesis Firehose delivery (use kinesis-firehose-troubshooter), or MSK (use kafka-msk-troubleshooter).
---

# Kinesis Data Analytics Deployer

An AWS CloudOps agent skill that deploys Amazon Kinesis Data Analytics
applications (Managed Service for Apache Flink and Studio SQL
applications) with correct production defaults. Emits a
READY_TO_DEPLOY checklist verifying every configuration item.

## Quick navigation

| Need | Section |
|---|---|
| What MUST be in the response | "STRICT output contract" |
| Why application-before-code order matters | "Reasoning framework" |
| What to verify before deploying | "Prerequisites" |
| The ordered deployment steps | "Deployment procedure" |
| Common silent-failure pitfalls | "NEVER" |
| SQL-vs-Flink decision matrix | "Workload matrix" |
| 2024-2026 feature changes | "Recent AWS features" |
| Deep CLI sequences | `references/cli-commands-and-iac.md` |
| Execution roles, parallelism, checkpoints, full NEVER | `references/execution-and-capacity-guide.md` |

## STRICT output contract

When this skill is invoked with a Kinesis Data Analytics deployment
request, the agent MUST respond with the READY_TO_DEPLOY checklist
defined in "Output format" using the literal all-caps labels
`APPLICATION:`, `VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`.
Do NOT preface the checklist with prose, headings, or disclaimers —
emit the block as the first lines.

### Required output structure

1. `APPLICATION: <application-name>` — the KDA application being
   deployed.
2. `VERDICT: READY_TO_DEPLOY` OR `VERDICT: PREREQUISITES_MISSING`.
3. `CHECKLIST:` followed by indented lines with status markers
   (`[✓]`, `[✗]`, `[OPTIONAL]`, `[INPUT NEEDED]`).
4. `VERIFICATION_COMMANDS:` followed by indented
   `aws kinesisanalyticsv2 ...` commands.

### FORBIDDEN output patterns

- **No prose preamble before `APPLICATION:`** — first non-empty line
  MUST be `APPLICATION:`.
- **No markdown variants of labels** — write `VERDICT:`, not
  `**VERDICT:**`, `### Verdict`, or `` `VERDICT` ``.
- **No swapping verdict tokens** — exactly `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`.
- **No omitting `VERIFICATION_COMMANDS:`** — include even when
  PREREQUISITES_MISSING.
- **No extra sections after `VERIFICATION_COMMANDS:`** — the
  checklist block is the entire response.
- **No status marker drift** — use only `[✓]`, `[✗]`, `[OPTIONAL]`,
  `[INPUT NEEDED]`.

### Perfect example (copy the shape exactly)

```text
APPLICATION: fraud-detection-flink
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Runtime environment — FLINK-1_19, application mode STREAMING
  [✓]      Service execution role — arn:aws:iam::123456789012:role/KDAExecutionRole (Kinesis read, Firehose write, CloudWatch Logs, S3 code)
  [✓]      Source — Kinesis Data Stream arn:aws:kinesis:us-east-1:123456789012:stream/transactions, starting position LATEST
  [✓]      Destination — Kinesis Data Stream arn:aws:aws...:stream/alerts, parallelism 4
  [✓]      Application code — s3://kda-apps/fraud-detection-1.0.0.jar (pinned, NOT latest)
  [✓]      Checkpointing — interval 60000 ms, min pause 5000 ms, configuration UPDATE
  [✓]      Parallelism — 4 (parallelismPerKPU 1, 4 KPUs total)
  [✓]      CloudWatch logging — enabled, log group /aws/kinesis-analytics/fraud-detection-flink
  [✓]      Snapshots — configured for stateful recovery
  [✓]      Tags — Environment=production, Application=fraud-detection
  [OPTIONAL] Studio notebook — Apache Zeppelin (not configured for this app)
VERIFICATION_COMMANDS:
  aws kinesisanalyticsv2 describe-application --application-name fraud-detection-flink
  aws iam get-role --role-name KDAExecutionRole
  aws kinesis describe-stream --stream-name transactions
  aws logs describe-log-groups --log-group-name-prefix /aws/kinesis-analytics/fraud-detection-flink
```

## Reasoning framework (why the application-before-code order matters)

1. **Application FIRST** — a KDA application is the container for all
   Flink/SQL streaming work. It defines the runtime environment
   (FLINK-1_19 or SQL-1_0), execution role, parallelism, and
   checkpointing. Without an application you cannot run code.
2. **Service execution role** — the IAM role the application assumes
   at runtime for Kinesis reads, Firehose/S3 writes, CloudWatch
   logging, and S3 code retrieval. Without it, the application fails
   to start with `AccessDeniedException` on the first source read.
3. **Source configuration** — Kinesis Data Stream or Firehose as the
   streaming source. Defines the stream ARN and starting position
   (LATEST, TRIM_HORIZON, or AT_TIMESTAMP). Without a source, the
   application starts but processes zero records.
4. **Destination configuration** — Kinesis Data Stream, Firehose, or
   S3 as the destination. SQL apps emit INSERT results; Flink apps
   write via sinks. Without a destination, processed records are
   dropped.
5. **Application code** — for Flink, a JAR/Python package in S3; for
   SQL, an in-line SQL script. Pin to a versioned key — NEVER `latest`
   or `/current/` paths.
6. **Checkpointing and parallelism LAST** — tuning parameters applied
   AFTER the application is created. Checkpointing enables stateful
   recovery; parallelism controls throughput. Changing them requires
   an application update.

## Prerequisites (verify before deployment)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| **IAM service execution role** | Trust `kinesisanalytics.amazonaws.com`. Scope for Kinesis/Firehose/S3/CloudWatch. NEVER `AdministratorAccess`. | `aws iam get-role --role-name <role>` |
| **Source Kinesis stream (or Firehose)** | MUST exist and be ACTIVE before the application reads. Without it, the source is empty. | `aws kinesis describe-stream --stream-name <name>` |
| **Destination resource** | Kinesis stream, Firehose delivery stream, or S3 bucket. MUST exist before the application writes. | `aws kinesis describe-stream` / `aws firehose describe-delivery-stream` / `aws s3 ls` |
| **S3 code bucket (Flink apps)** | Stores the application JAR/Python package. MUST exist with the code object. | `aws s3 ls s3://<bucket>/<key>` |
| **CloudWatch log group** | KDA streams application logs and Flink TaskManager logs. Recommended for production. | `aws logs describe-log-groups --log-group-name-prefix /aws/kinesis-analytics/` |
| **Runtime environment** | `FLINK-1_19` (or SQL-1_0 for legacy SQL). Determines engine version. Use the latest stable Flink runtime. | `aws kinesisanalyticsv2 list-applications` (check similar apps) |
| **Service quota** | Default KPUs per Region per account. Request increase BEFORE production. | `aws service-quotas get-service-quota --service-code kinesisanalytics --quota-code L-XXXXXXXX` |
| **VPC configuration (if private sources)** | If the app reads from private MSK or private OpenSearch, VPC subnets and security groups are REQUIRED. | `aws ec2 describe-subnets --subnet-ids <ids>` |
| **Glue schema registry (if avro/protobuf)** | Source records using Avro/Protobuf MUST have a schema in the registry for Flink to deserialize. | `aws glue get-registry --registry-name <name>` |

## Deployment procedure (apply in order)

### Step 1: IAM service execution role

The service execution role is assumed by the KDA application for all
runtime AWS API calls (Kinesis reads, Firehose writes, S3 code
retrieval, CloudWatch logging). Without it, the application fails on
the first source read.

```bash
aws iam create-role \
  --role-name KDAExecutionRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "kinesisanalytics.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name KDAExecutionRole \
  --policy-name kda-exec \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["kinesis:GetRecords", "kinesis:GetShardIterator", "kinesis:DescribeStream", "kinesis:ListShards"],
        "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/transactions"
      },
      {
        "Effect": "Allow",
        "Action": ["kinesis:PutRecord", "kinesis:PutRecords"],
        "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/alerts"
      },
      {
        "Effect": "Allow",
        "Action": ["s3:GetObject"],
        "Resource": "arn:aws:s3:::kda-apps/fraud-detection-1.0.0.jar"
      },
      {
        "Effect": "Allow",
        "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogGroups"],
        "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/kinesis-analytics/*"
      },
      {
        "Effect": "Allow",
        "Action": ["kinesisanalytics:CreateApplicationSnapshot", "kinesisanalytics:DeleteApplicationSnapshot", "kinesisanalytics:DescribeApplicationSnapshot"],
        "Resource": "arn:aws:kinesisanalytics:us-east-1:123456789012:application/fraud-detection-flink"
      }
    ]
  }'
```

Rules:
- **Trust `kinesisanalytics.amazonaws.com`** — NOT
  `firehose.amazonaws.com` (separate service principal).
- **NEVER use `AdministratorAccess`** — scope to the specific Kinesis
  streams, Firehose delivery streams, and S3 code objects the app
  needs.
- **CloudWatch Logs permissions** — required for application log
  delivery and Flink framework errors.
- **Pass role for KDA-created resources** — if the app creates
  snapshots, include `kinesisanalytics:*ApplicationSnapshot`.

### Step 2: Confirm source stream exists

```bash
aws kinesis describe-stream --stream-name transactions \
  --query 'StreamDescription.{Status:StreamStatus,ARN:StreamARN,Shards:Shards[*].ShardId}'
# StreamStatus MUST be ACTIVE
```

For Firehose source:

```bash
aws firehose describe-delivery-stream --delivery-stream-name ingestion-stream \
  --query 'DeliveryStreamDescription.{Status:DeliveryStreamStatus,ARN:DeliveryStreamARN}'
# DeliveryStreamStatus MUST be ACTIVE
```

### Step 3: Create the application (Flink)

```bash
aws kinesisanalyticsv2 create-application \
  --application-name fraud-detection-flink \
  --runtime-environment FLINK-1_19 \
  --service-execution-role arn:aws:iam::123456789012:role/KDAExecutionRole \
  --application-configuration '{
    "ApplicationCodeConfiguration": {
      "CodeContent": {
        "S3ContentLocation": {
          "BucketARN": "arn:aws:s3:::kda-apps",
          "FileKey": "fraud-detection-1.0.0.jar"
        },
        "CodeContentType": "ZIPFILE"
      },
      "CodeContentType": "ZIPFILE"
    },
    "FlinkApplicationConfiguration": {
      "CheckpointConfiguration": {
        "ConfigurationType": "CUSTOM",
        "CheckpointingEnabled": true,
        "CheckpointInterval": 60000,
        "MinPauseBetweenCheckpoints": 5000
      },
      "ParallelismConfiguration": {
        "ConfigurationType": "CUSTOM",
        "Parallelism": 4,
        "ParallelismPerKPU": 1
      },
      "MonitoringConfiguration": {
        "ConfigurationType": "CUSTOM",
        "MetricsLevel": "APPLICATION",
        "LogLevel": "INFO",
        "LogStreamARN": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/kinesis-analytics/fraud-detection-flink"
      }
    },
    "EnvironmentProperties": {
      "PropertyGroups": [
        {"PropertyGroupId": "ConsumerConfig", "PropertyMap": {"STREAM_NAME": "transactions", "AWS_REGION": "us-east-1", "SCAN_START_POSITION": "LATEST"}}
      ]
    },
    "ApplicationSnapshotConfiguration": {
      "SnapshotsEnabled": true
    }
  }' \
  --tags Environment=production,Application=fraud-detection
```

### Step 4: Create the application (SQL)

```bash
aws kinesisanalyticsv2 create-application \
  --application-name session-windows-sql \
  --runtime-environment SQL-1_0 \
  --service-execution-role arn:aws:iam::123456789012:role/KDAExecutionRole \
  --application-configuration '{
    "SqlApplicationConfiguration": {
      "Inputs": [{
        "NamePrefix": "SOURCE_SQL_STREAM",
        "KinesisStreamsInput": {
          "ResourceARN": "arn:aws:kinesis:us-east-1:123456789012:stream/clicks",
          "RoleARN": "arn:aws:iam::123456789012:role/KDAExecutionRole"
        },
        "InputSchema": {
          "RecordFormat": {"RecordFormatType": "JSON"},
          "RecordColumns": [
            {"Name": "event_time", "SqlType": "TIMESTAMP", "Mapping": "$.event_time"},
            {"Name": "user_id", "SqlType": "VARCHAR(64)", "Mapping": "$.user_id"},
            {"Name": "event_type", "SqlType": "VARCHAR(32)", "Mapping": "$.event_type"}
          ]
        },
        "InputParallelism": {"Count": 1},
        "InputStartingPositionConfiguration": {"InputStartingPosition": "NOW"}
      }]
    },
    "ApplicationCodeConfiguration": {
      "CodeContent": {
        "TextInput": "CREATE OR REPLACE PUMP \"SESSION_PUMP\" AS INSERT INTO DESTINATION_SQL_STREAM SELECT STREAM user_id, COUNT(*) AS event_count, SESSION_START() AS window_start, SESSION_END() AS window_end FROM SOURCE_SQL_STREAM_001 GROUP BY user_id, SESSION(event_time, INTERVAL '\''60'\'' SECONDS);"
      },
      "CodeContentType": "INLINE"
    }
  }' \
  --tags Environment=production,Application=session-windows
```

### Step 5: Configure source via CloudWatch log group

```bash
aws logs create-log-group \
  --log-group-name /aws/kinesis-analytics/fraud-detection-flink
```

### Step 6: Start the application

```bash
aws kinesisanalyticsv2 start-application \
  --application-name fraud-detection-flink \
  --run-configuration '{
    "FlinkRunConfiguration": {"AllowNonRestoredState": false},
    "SqlRunConfigurations": [],
    "ApplicationRestoreConfiguration": {
      "RestoreType": "RESTORE_FROM_LATEST_SNAPSHOT"
    }
  }'
```

Wait for `RUNNING` state:

```bash
aws kinesisanalyticsv2 describe-application \
  --application-name fraud-detection-flink \
  --query 'ApplicationDetail.ApplicationStatus'
# Should return 'RUNNING'
```

### Step 7: Checkpointing (Flink stateful recovery)

> **Moved verbatim** → [references/execution-and-capacity-guide.md](references/execution-and-capacity-guide.md) § "Step 7: Checkpointing (Flink stateful recovery)".
> Load when: configuring Flink checkpointing — interval, min pause, AllowNonRestoredState rules.

### Step 8: Parallelism tuning

> **Moved verbatim** → [references/execution-and-capacity-guide.md](references/execution-and-capacity-guide.md) § "Step 8: Parallelism tuning".
> Load when: sizing parallelism and KPUs — matching parallelism to shard count, ParallelismPerKPU, JobManager overhead.

### Step 9: Studio notebook (Zeppelin, interactive analysis)

> **Moved verbatim** → [references/execution-and-capacity-guide.md](references/execution-and-capacity-guide.md) § "Step 9: Studio notebook (Zeppelin, interactive analysis)".
> Load when: creating a Studio notebook — Zeppelin application config, custom artifacts, promotion to a production app.

### Step 10: Application snapshots (stateful recovery)

> **Moved verbatim** → [references/execution-and-capacity-guide.md](references/execution-and-capacity-guide.md) § "Step 10: Application snapshots (stateful recovery)".
> Load when: using snapshots for stateful recovery — create/list snapshots and RESTORE_FROM_CUSTOM_SNAPSHOT starts.

### Step 11: Verification

```bash
aws kinesisanalyticsv2 describe-application --application-name fraud-detection-flink
aws kinesisanalyticsv2 describe-application --application-name fraud-detection-flink --query 'ApplicationDetail.ApplicationStatus'
aws iam get-role --role-name KDAExecutionRole
aws kinesis describe-stream --stream-name transactions
aws logs describe-log-groups --log-group-name-prefix /aws/kinesis-analytics/fraud-detection-flink
aws kinesisanalyticsv2 list-application-snapshots --application-name fraud-detection-flink
```

## Recent AWS features (2024-2026)

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Recent AWS features (2024-2026)".
> Load when: checking 2024-2026 feature availability — session windows, snapshots, Flink 1.19, Glue Catalog, VPC sources.

## Workload matrix

| Workload | Runtime | Source | Destination | Parallelism | Checkpointing | Studio notebook |
|---|---|---|---|---|---|---|
| **Fraud detection (Flink)** | FLINK-1_19 | Kinesis Stream | Kinesis Stream | 4-8 | 60s interval | No |
| **Sessionization (SQL)** | SQL-1_0 | Kinesis Stream | Kinesis Stream | 1-2 | N/A (SQL) | No |
| **Click analytics (SQL)** | SQL-1_0 | Kinesis Stream | Firehose | 1 | N/A (SQL) | No |
| **Anomaly detection (Flink)** | FLINK-1_19 | Kinesis Stream | S3 via Firehose | 8 | 30s interval | No |
| **Exploratory analysis (Zeppelin)** | ZEPPELIN-FLINK-1_0 | Kinesis Stream | (notebook output) | 2 | Optional | Yes |
| **ETL enrichment (Flink)** | FLINK-1_19 | Kinesis Stream | Firehose to S3 | 4 | 60s interval | No |
| **Alerting (SQL lambdas)** | SQL-1_0 | Kinesis Stream | Lambda via Firehose | 1 | N/A (SQL) | No |
| **Dev/test** | FLINK-1_19 | Kinesis Stream | Kinesis Stream | 1 | 120s interval | Optional |

## NEVER (top 5 — full list of 12 in references)

- NEVER start a KDA application that has no service execution role
  configured. The application fails immediately with
  `AccessDeniedException` on the first Kinesis `GetRecords` call. The
  execution role is the #1 prerequisite for KDA.
- NEVER use `AdministratorAccess` on the service execution role. Scope
  to the specific Kinesis streams, Firehose delivery streams, and S3
  code objects the app needs. KDA applications run arbitrary streaming
  code — a broad role is a privilege escalation vector.
- NEVER deploy a Flink application that reads from a Kinesis stream
  with fewer shards than `Parallelism`. Sub-parallelism wastes KPUs.
  Match `Parallelism` to the source shard count for full utilization.
- NEVER disable checkpointing in production. A failure means full
  state loss and replay from the earliest unprocessed record. For
  stateful Flink apps, checkpoints are the ONLY recovery mechanism.
- NEVER use `latest` or unversioned S3 keys for application code. KDA
  pulls the code at application start — a new push silently changes
  what runs. Pin to a versioned key (e.g., `fraud-detection-1.0.0.jar`)
  or SHA suffix. #1 reproducibility breaker.

## Expert heuristic — parallelism, checkpoints, and SQL-vs-Flink strategy

> **Moved verbatim** → [references/execution-and-capacity-guide.md](references/execution-and-capacity-guide.md) § "Expert heuristic — parallelism, checkpoints, and SQL-vs-Flink strategy".
> Load when: tuning strategy — SQL-vs-Flink selection, session-window gaps, parallelism sizing, checkpoint intervals, log retention.

## Pre-flight safety checks (run before any deployment CLI)

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Pre-flight safety checks (run before any deployment CLI)".
> Load when: about to run any deployment CLI — the confirmation checklist covering role, streams, code object, quota, log group.

## Output format — MANDATORY literal labels

When invoked with a Kinesis Data Analytics deployment request, your
ENTIRE response MUST be the checklist block below. The labels are
**case-sensitive all-caps keywords**. Do NOT write a preamble. Start
with `APPLICATION:` and stop after the `VERIFICATION_COMMANDS:` block.

```text
APPLICATION: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓]      Runtime environment — FLINK-1_19 | SQL-1_0 | ZEPPELIN-FLINK-1_0
  [✓]      Service execution role — <role-arn> (<scoped-permissions>)
  [✓]      Source — Kinesis Data Stream | Firehose, <stream-arn>, starting position <LATEST | TRIM_HORIZON | NOW>
  [✓]      Destination — Kinesis Data Stream | Firehose | S3, <resource-arn>, parallelism <n>
  [✓]      Application code — s3://<bucket>/<key> (Flink) | inline SQL (SQL)
  [✓]      Checkpointing — interval <ms>, min pause <ms>, configuration CUSTOM | DEFAULT
  [✓]      Parallelism — <n> (parallelismPerKPU <n>, <total> KPUs)
  [✓]      CloudWatch logging — enabled, log group <log-group>
  [✓]      Tags — <tags>
  [OPTIONAL] Studio notebook — Apache Zeppelin (configured | not configured)
  [OPTIONAL] Application snapshots — enabled for stateful recovery
VERIFICATION_COMMANDS:
  aws kinesisanalyticsv2 describe-application --application-name <name>
  aws iam get-role --role-name <exec-role>
  aws kinesis describe-stream --stream-name <source-stream>
  aws logs describe-log-groups --log-group-name-prefix /aws/kinesis-analytics/<name>
```

**Status marker semantics:**
- `[✓]` — applied and verified.
- `[✗]` — NOT applied or misconfigured. Cite the gap.
- `[OPTIONAL]` — recommended but not required.
- `[INPUT NEEDED]` — prerequisite value missing; operator must provide.

**PREREQUISITES_MISSING verdict:** if any REQUIRED prerequisite is
missing (execution role, source stream, destination resource, S3 code
object for Flink apps), the verdict is `PREREQUISITES_MISSING`.

## References (load on demand)

- [references/cli-commands-and-iac.md](references/cli-commands-and-iac.md) — full copy-pasteable CLI sequence for all 11 deployment steps with Terraform / CloudFormation equivalents (existing)
- [references/execution-and-capacity-guide.md](references/execution-and-capacity-guide.md) — checkpointing, parallelism and KPU tuning, Studio notebook setup, application snapshots, expert SQL-vs-Flink heuristics (moved verbatim; existing deep reference)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight safety checks to run before any deployment CLI
- [references/advanced-patterns.md](references/advanced-patterns.md) — edge-case handling (cross-account sources, schema evolution, VPC sources) and recent AWS features 2024-2026

## Domain

AWS CloudOps / Kinesis Data Analytics Streaming Compute Provisioning.

## Edge-case handling

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Edge-case handling".
> Load when: hitting an edge case — cross-account sources, schema evolution, snapshot restore with code changes, VPC/private MSK sources.

## AWS documentation

- **Kinesis Data Analytics Developer Guide** — https://docs.aws.amazon.com/kinesisanalytics/latest/java/getting-started.html
- **CreateApplication API (v2)** — https://docs.aws.amazon.com/kinesisanalyticsv2/latest/APIReference/API_CreateApplication.html
- **Managed Service for Apache Flink** — https://docs.aws.amazon.com/managed-flink/latest/applaunchboard/what-is-managed-flink.html
- **Flink Application Configuration** — https://docs.aws.amazon.com/kinesisanalytics/latest/java/application-config.html
- **Checkpointing** — https://docs.aws.amazon.com/managed-flink/latest/applaunchboard/checkpointing.html
- **Parallelism** — https://docs.aws.amazon.com/managed-flink/latest/applaunchboard/parallelism.html
- **Studio Notebooks** — https://docs.aws.amazon.com/kinesisanalytics/latest/studio/getting-started.html
- **Application Snapshots** — https://docs.aws.amazon.com/managed-flink/latest/applaunchboard/app-snapshots.html
- **Session Windows SQL** — https://docs.aws.amazon.com/kinesisanalytics/latest/dev/sql-app-session-windows.html
- **Kinesis Analytics CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/kinesisanalyticsv2/

## References

- `references/cli-commands-and-iac.md` — full copy-pasteable CLI command
  sequence for all 11 deployment steps, including execution role
  creation, source stream verification, Flink/SQL application
  creation, checkpointing and parallelism configuration, Studio
  notebook setup, application snapshots, and Terraform /
  CloudFormation equivalents.

- `references/execution-and-capacity-guide.md` — deep reference on
  service execution role scoping, parallelism and KPU tuning,
  checkpointing strategy, snapshot-based recovery, Studio notebook
  promotion, SQL windowing patterns (session, hopping, tumbling),
  VPC source configuration, full NEVER list, edge-case handling, and
  pre-flight safety CLI.
