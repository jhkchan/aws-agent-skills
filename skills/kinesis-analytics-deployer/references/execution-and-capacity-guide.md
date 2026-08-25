# Execution and Capacity Guide — Kinesis Data Analytics Deployer

Deep reference on service execution role scoping, parallelism and KPU
tuning, checkpointing strategy, snapshot-based recovery, Studio
notebook promotion, SQL windowing patterns (session, hopping,
tumbling), VPC source configuration, the full NEVER list, edge-case
handling, and pre-flight safety CLI.

## Service execution role scoping

### Trust policy

The service execution role MUST trust
`kinesisanalytics.amazonaws.com`. NOT `firehose.amazonaws.com` (that
is the Firehose principal) or `kinesis.amazonaws.com` (the Kinesis
Data Streams principal). Mixing them produces
`AccessDeniedException`.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "kinesisanalytics.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

### Permission scoping matrix

| Workload | Required permissions |
|---|---|
| **Kinesis source read** | `kinesis:GetRecords`, `kinesis:GetShardIterator`, `kinesis:DescribeStreamSummary`, `kinesis:ListShards` on source stream ARN |
| **Kinesis destination write** | `kinesis:PutRecord`, `kinesis:PutRecords` on destination stream ARN |
| **Firehose source read** | `firehose:Get*` on source delivery stream ARN |
| **Firehose destination write** | `firehose:PutRecord`, `firehose:PutRecordBatch` on destination ARN |
| **S3 code retrieval** | `s3:GetObject` on the code object ARN |
| **CloudWatch Logs** | `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`, `logs:DescribeLogGroups` on the log group ARN |
| **Application snapshots** | `kinesisanalytics:CreateApplicationSnapshot`, `kinesisanalytics:DeleteApplicationSnapshot`, `kinesisanalytics:DescribeApplicationSnapshot` |
| **VPC access (private sources)** | `ec2:CreateNetworkInterface`, `ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface` |
| **Glue schema registry** | `glue:GetSchemaVersion`, `glue:GetSchemaByDefinition` |

### Common mistakes

- **`Resource: "*"`** — NEVER use wildcard resources. Scope each
  statement to the specific stream ARN, S3 object ARN, and log group
  ARN.
- **Missing `kinesis:ListShards`** — required for shard discovery on
  resharding events. Without it, the app stops processing after a
  shard split/merge.
- **Missing `logs:CreateLogGroup`** — KDA creates the log group on
  first start. Without it, application logs are silently dropped.

## Parallelism and KPU tuning

### The parallelism-to-shard rule

Set `Parallelism` to the source Kinesis stream shard count. Each
Flink subtask consumes one or more shards. If `Parallelism < shard
count`, subtasks read multiple shards (still correct, but less
parallelism). If `Parallelism > shard count`, extra subtasks read no
shards (wasted KPUs).

### KPU calculation

Total KPUs = (Parallelism / ParallelismPerKPU) + 1 (JobManager
reserve, when ParallelismPerKPU = 1).

For memory-heavy workloads, lower `ParallelismPerKPU` (default 1)
gives each subtask a full KPU (4 GB memory). For CPU-light workloads,
raise `ParallelismPerKPU` to 2 or 4 to densify subtasks onto fewer
KPUs.

| Workload | Parallelism | ParallelismPerKPU | KPUs |
|---|---|---|---|
| 4-shard stream, CPU-heavy | 4 | 1 | 5 |
| 4-shard stream, CPU-light | 4 | 2 | 3 |
| 8-shard stream, ML inference | 8 | 1 | 9 |
| 2-shard stream, simple filter | 2 | 1 | 3 |

## Checkpointing strategy

### Why checkpointing matters

Checkpoints persist Flink operator state to S3 at regular intervals.
On failure, the application restarts from the latest checkpoint
without losing in-flight data. This is the ONLY recovery mechanism
for stateful Flink apps.

### Interval tuning

| Interval | Use case | Tradeoff |
|---|---|---|
| 30s | Low-latency (< 1s processing) | Higher overhead, faster recovery |
| 60s (default) | Most production apps | Balanced |
| 120s | High-throughput batch-like | Lower overhead, slower recovery |
| < 5s | NEVER | Checkpoint storms destabilize the JobManager |

### Min pause between checkpoints

`MinPauseBetweenCheckpoints` (default 5000 ms) ensures the current
checkpoint completes before the next starts. If checkpoints take
longer than `CheckpointInterval - MinPauseBetweenCheckpoints`, they
are skipped. NEVER set below 5000 ms.

## Snapshot-based recovery

### Snapshots vs checkpoints

| Feature | Checkpoint | Snapshot |
|---|---|---|
| Trigger | Automatic (interval) | User-triggered |
| Purpose | Failure recovery | Planned stop/start, code updates |
| Retention | Latest only | Named, retained until deleted |
| Use case | Production fault tolerance | Code deploys, blue/green |

### Snapshot workflow for code updates

1. Create a snapshot: `create-application-snapshot`
2. Update application code: `update-application`
3. Start from snapshot: `start-application` with
   `RESTORE_FROM_CUSTOM_SNAPSHOT`

### AllowNonRestoredState

If the new code removed a Flink operator, the snapshot restore fails
with `AllowNonRestoredState: false`. Set to `true` ONLY during
verified breaking changes — otherwise you silently drop state.

## SQL windowing patterns

### Session windows

Groups events into sessions with inactivity gaps. Use for user
behavior analytics (web sessions, mobile sessions).

```sql
CREATE OR REPLACE PUMP "SESSION_PUMP" AS
INSERT INTO DESTINATION_SQL_STREAM
SELECT STREAM
  user_id,
  COUNT(*) AS event_count,
  SESSION_START() AS window_start,
  SESSION_END() AS window_end
FROM SOURCE_SQL_STREAM_001
GROUP BY user_id, SESSION(event_time, INTERVAL '60' SECONDS);
```

Tune the gap to the domain: 30 min for web sessions, 5 min for
mobile, 60s for real-time alerts.

### Hopping windows

Fixed-size windows that overlap. Use for smoothed aggregates.

```sql
CREATE OR REPLACE PUMP "HOP_PUMP" AS
INSERT INTO DESTINATION_SQL_STREAM
SELECT STREAM
  user_id,
  AVG(value) AS avg_value,
  FLOOR("SOURCE_SQL_STREAM_001".ROWTIME TO MINUTE) AS window_start
FROM SOURCE_SQL_STREAM_001
GROUP BY user_id, FLOOR("SOURCE_SQL_STREAM_001".ROWTIME TO MINUTE);
```

### Tumbling windows

Fixed-size, non-overlapping windows. Use for periodic aggregates.

```sql
CREATE OR REPLACE PUMP "TUMBLE_PUMP" AS
INSERT INTO DESTINATION_SQL_STREAM
SELECT STREAM
  STEP("SOURCE_SQL_STREAM_001".ROWTIME BY INTERVAL '60' SECOND) AS window_start,
  STEP("SOURCE_SQL_STREAM_001".ROWTIME BY INTERVAL '60' SECOND) + INTERVAL '60' SECOND AS window_end,
  COUNT(*) AS event_count
FROM SOURCE_SQL_STREAM_001
GROUP BY STEP("SOURCE_SQL_STREAM_001".ROWTIME BY INTERVAL '60' SECOND);
```

## VPC source configuration

KDA applications can connect to private MSK, private OpenSearch, and
private RDS via VPC subnets and security groups.

```json
{
  "VpcConfiguration": {
    "SubnetIds": ["subnet-aaa", "subnet-bbb"],
    "SecurityGroupIds": ["sg-kda-prod"]
  }
}
```

Rules:
- **Use PRIVATE subnets.** KDA applications do not need public IPs.
- **Span at least 2 AZs** (3 for production HA).
- **Security group outbound** must allow the destination port
  (9092 for MSK plaintext, 9200 for OpenSearch, 5432 for Postgres).
- **NAT Gateway is NOT required** for S3/Kinesis access — use VPC
  gateway endpoints. NAT is only needed for external API calls.

## NEVER (full list)

1. NEVER start a KDA application that has no service execution role.
   The application fails with `AccessDeniedException` on the first
   Kinesis `GetRecords` call.
2. NEVER use `AdministratorAccess` on the execution role. Scope to
   the specific Kinesis streams, Firehose delivery streams, and S3
   code objects.
3. NEVER deploy a Flink app reading from a stream with fewer shards
   than `Parallelism`. Sub-parallelism wastes KPUs.
4. NEVER disable checkpointing in production. Failure means full
   state loss and replay from the earliest unprocessed record.
5. NEVER use `latest` or unversioned S3 keys for application code.
   Pin to a versioned key (e.g., `fraud-detection-1.0.0.jar`).
6. NEVER change parallelism without a snapshot if the app is
   stateful. Flink redistributes operator state across subtasks.
7. NEVER run production traffic through a Studio notebook. They
   are billed per-second and lack checkpoint guarantees.
8. NEVER use SQL-1_0 for complex stateful processing. Use Flink
   for CEP, custom operators, and ML inference.
9. NEVER set `MinPauseBetweenCheckpoints` below 5000 ms. Checkpoint
   storms destabilize the JobManager.
10. NEVER leave CloudWatch Logs at default (Never Expire). Set
    14-30 day retention.
11. NEVER make breaking Glue schema changes without an application
    update. KDA Flink apps auto-use the latest schema version.
12. NEVER mix trust principals. Use `kinesisanalytics.amazonaws.com`,
    not `firehose.amazonaws.com`.

## Pre-flight safety CLI

```bash
# Execution role trust
aws iam get-role --role-name <exec-role> --query 'Role.AssumeRolePolicyDocument'

# Source stream active
aws kinesis describe-stream --stream-name <source-stream> --query 'StreamDescription.StreamStatus'

# Destination resource active
aws kinesis describe-stream --stream-name <dest-stream> --query 'StreamDescription.StreamStatus'

# S3 code object exists
aws s3 ls s3://<code-bucket>/<code-key>

# CloudWatch log group
aws logs describe-log-groups --log-group-name-prefix /aws/kinesis-analytics/

# VPC subnets (if private sources)
aws ec2 describe-subnets --subnet-ids <subnet-ids>

# Glue schema (if Avro/Protobuf)
aws glue get-schema-version --schema-id '{"SchemaName":"<name>","RegistryName":"<registry>"}' --schema-version-number LatestVersion

# Service quota
aws service-quotas get-service-quota --service-code kinesisanalytics --quota-code L-XXXXXXXX
```

## Step 7: Checkpointing (Flink stateful recovery) (moved from SKILL.md)

Checkpointing persists Flink operator state to S3 so the application
can recover from failures without losing in-flight data.

| Parameter | Default | Production | Why |
|---|---|---|---|
| `CheckpointingEnabled` | true | true | Stateful recovery. NEVER disable in production. |
| `CheckpointInterval` | 60000 ms | 30000-120000 ms | Shorter = faster recovery but more overhead. |
| `MinPauseBetweenCheckpoints` | 5000 ms | 5000-10000 ms | Ensures checkpoints complete before the next starts. |
| `ConfigurationType` | DEFAULT | CUSTOM | CUSTOM lets you override intervals. |

Rules:
- **NEVER disable checkpointing in production.** A failure means full
  state loss and replay from the earliest unprocessed record.
- **Pair with snapshots** for planned stop/start. Snapshots are
  user-triggered; checkpoints are automatic.
- **`AllowNonRestoredState: false`** — set on start to fail fast if
  the code change removed an operator. Set to `true` only during
  breaking changes with manual verification.

## Step 8: Parallelism tuning (moved from SKILL.md)

Parallelism controls how many Flink subtasks process the stream
concurrently. KPUs (Kinesis Processing Units) are the billing unit
(1 KPU = 1 vCPU, 4 GB memory).

| Parameter | Default | Production | Why |
|---|---|---|---|
| `Parallelism` | 1 | 2-8 (tune to shard count) | Must be >= source shard count for full parallelism. |
| `ParallelismPerKPU` | 1 | 1 (default) | Lower = more KPUs per subtask (more memory). Higher = denser packing. |
| Total KPUs | parallelism + 1 (JobManager) | auto | Billed per-second. Tune to workload. |

Rules:
- **Match parallelism to source shards.** If the source Kinesis stream
  has 4 shards, set `Parallelism: 4`. Sub-parallelism wastes KPUs.
- **ParallelismPerKPU > 1** densifies subtasks onto fewer KPUs —
  useful for CPU-light workloads. Default 1 for memory-heavy.
- **JobManager overhead** — KDA reserves 1 KPU for the JobManager.
  Total KPUs = parallelism + 1 (when ParallelismPerKPU = 1).

## Step 9: Studio notebook (Zeppelin, interactive analysis) (moved from SKILL.md)

Studio notebooks provide an interactive Apache Zeppelin environment
connected to live Kinesis streams for exploratory analysis. They
share the same KDA application runtime.

```bash
aws kinesisanalyticsv2 create-application \
  --application-name fraud-explore-notebook \
  --runtime-environment ZEPPELIN-FLINK-1_0 \
  --service-execution-role arn:aws:iam::123456789012:role/KDAExecutionRole \
  --application-configuration '{
    "ZeppelinApplicationConfiguration": {
      "MonitoringConfiguration": {
        "LogLevel": "INFO"
      },
      "CatalogConfiguration": {
        "GlueDataCatalogConfiguration": {
          "DatabaseARN": "arn:aws:glue:us-east-1:123456789012:database/default"
        }
      },
      "CustomArtifactsConfiguration": [
        {"ArtifactType": "UDF", "S3ContentLocation": {"BucketARN": "arn:aws:s3:::kda-apps", "FileKey": "custom-udf-1.0.0.jar"}, "MavenReference": {"ArtifactId": "", "GroupId": "", "Version": ""}}
      ],
      "DeployAsApplicationConfiguration": {
        "CreateApplicationAsReadyForDeployment": true
      }
    }
  }' \
  --tags Environment=dev,Application=fraud-explore
```

Rules:
- **Studio notebooks are for exploration** — NOT production pipelines.
  Deploy production Flink code as a STREAMING application, not a
  Zeppelin notebook.
- **Zeppelin paragraphs persist** — notebooks can be saved to S3 for
  team sharing.
- **`DeployAsApplicationConfiguration`** — promotes a notebook to a
  production STREAMING application once exploration is complete.

## Step 10: Application snapshots (stateful recovery) (moved from SKILL.md)

```bash
# Create a snapshot before a code update
aws kinesisanalyticsv2 create-application-snapshot \
  --application-name fraud-detection-flink \
  --snapshot-name pre-update-2026-08-11

# List snapshots
aws kinesisanalyticsv2 list-application-snapshots \
  --application-name fraud-detection-flink

# Update application code, then start from snapshot
aws kinesisanalyticsv2 start-application \
  --application-name fraud-detection-flink \
  --run-configuration '{
    "ApplicationRestoreConfiguration": {
      "RestoreType": "RESTORE_FROM_CUSTOM_SNAPSHOT",
      "SnapshotName": "pre-update-2026-08-11"
    }
  }'
```

## Expert heuristic — parallelism, checkpoints, and SQL-vs-Flink strategy (moved from SKILL.md)

- **SQL-vs-Flink decision:** use SQL for simple stateless
  transformations, windowed aggregates, and lambdas. Use Flink for
  complex stateful processing, custom operators, CEP (complex event
  processing), and ML inference. SQL is faster to deploy; Flink is
  more expressive.
- **Session windows in SQL:** the `SESSION(window_col, INTERVAL 'N'
  SECONDS)` function groups events into sessions with inactivity gaps.
  Use for user behavior analytics. Tune the gap (default 60s) to the
  domain — 30 min for web sessions, 5 min for mobile.
- **Parallelism sizing:** set `Parallelism` to the source shard count.
  For CPU-heavy processing, increase `ParallelismPerKPU` to densify.
  For memory-heavy processing, keep `ParallelismPerKPU = 1` (1 KPU per
  subtask, 4 GB memory each).
- **Checkpoint interval tuning:** 60s is the default. For low-latency
  apps (sub-second processing), use 30s. For high-throughput batch-like
  processing, 120s reduces overhead. NEVER set below 5s — checkpoint
  storms destabilize the JobManager.
- **Snapshot before code updates:** ALWAYS create a snapshot before
  updating application code. Start the updated app with
  `RESTORE_FROM_CUSTOM_SNAPSHOT` to preserve state. Without this, a
  code update loses all in-flight state.
- **Studio notebook promotion:** explore in a Zeppelin notebook, then
  promote to a STREAMING application via
  `DeployAsApplicationConfiguration`. NEVER run production traffic
  through a notebook — they are billed per-second and lack checkpoint
  guarantees.
- **Firehose destination vs Kinesis stream destination:** use Firehose
  for S3/Redshift/OpenSearch delivery (batched, at-least-once). Use a
  Kinesis stream for downstream real-time consumers (sub-second,
  exactly-once with Flink sinks).
- **Log retention:** set CloudWatch Logs retention to 14-30 days.
  NEVER leave at default (Never Expire) — Flink framework logs are
  verbose and costs balloon.

