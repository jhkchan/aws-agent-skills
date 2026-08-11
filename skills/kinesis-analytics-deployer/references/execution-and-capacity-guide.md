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
