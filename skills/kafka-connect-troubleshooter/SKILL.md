---
name: kafka-connect-troubleshooter
description: Diagnoses Kafka Connect and Amazon MSK Connect issues through a nine-category diagnostic tree — task FAILED status (task exceptions), worker rebalance storms (consumer group coordinator churn), source connector lag (LagMax, offset not advancing), sink connector errors (DLQ config, retry exhaustion), schema registry connectivity (Avro/JSON/Protobuf, Confluent, Glue Schema Registry), IAM auth for MSK (kafka-cluster principal), plugin or connector class not found (custom plugin, Debezium), config errors (wrong topics, bootstrap servers, converter mismatch), and Single Message Transforms (SMT chain, Cast, ExtractTopic). Reads describe-connector or REST API status, CloudWatch logs (/aws/kafkaconnect/), and MSK describe-cluster for bootstrap and IAM validation. Emits ROOT_CAUSE_FOUND with the failing probe, NEED_MORE_INFO when a probe requires operator input, or ESCALATE for AWS-side incidents. Use when a connector shows FAILED, task FAILED, source lag grows, sink DLQ fills, or a plugin will not start.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works from a pasted connector status JSON, CloudWatch Logs excerpt, or worker error. Live-account diagnosis uses aws kafkaconnect describe-connector / list-connectors / update-connector; aws kafka describe-cluster / get-bootstrap-brokers; aws logs filter-log-events on /aws/kafkaconnect/; aws ec2 describe-security-groups; aws glue get-schema-registry or the Confluent Schema Registry REST...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing a Kafka Connect or Amazon MSK Connect connector that FAILED, has tasks in FAILED state, is stuck in worker rebalance, is showing growing source lag (LagMax climbing), is filling the DLQ, is failing schema-registry lookups (Avro/JSON/Protobuf), is unable to authenticate to MSK via IAM, is reporting class not found for a custom plugin or Debezium connector, or is surfacing Single Message Transforms errors.
  when_not_to_use: MSK cluster creation / capacity planning — use an MSK deploy skill, not a diagnostic., Kafka producer / consumer application bugs outside Connect — use a Kafka client troubleshooter., Kafka topic configuration (partitions, retention) — use an MSK admin skill., Schema evolution compatibility strategy — use a Schema Registry design skill; this skill diagnoses connectivity.
  activation_triggers: Kafka Connect failed, MSK Connect connector FAILED, Kafka Connect task FAILED, connector class not found, Kafka Connect worker rebalance, source connector lag growing, LagMax Kafka Connect, sink connector DLQ full, dead letter queue overflow, schema registry connection refused, Avro serializer error, MSK IAM authentication failed, Debezium connector not starting, Single Message Transform error, SMT Cast error, custom plugin upload failed, bootstrap servers wrong, diagnose Kafka Connect failure
  invocation_schema: 'Input: either (a) a connector name + live-account context (MSK Connect), (b) a pasted connector status JSON from the REST API or describe-connector, OR (c) a CloudWatch Logs excerpt from /aws/kafkaconnect/. Output: a deterministic TARGET / VERDICT / REASON / CATEGORY / EVIDENCE / REMEDIATION block per connector, where VERDICT is {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and CATEGORY is {TASK_EXCEPTION, WORKER_REBALANCE, SOURCE_LAG, SINK_DLQ, SINK_RETRY, SCHEMA_REGISTRY, IAM_AUTH, PLUGIN_MISSING, CONFIG_ERROR, SMT_ERROR, DEBEZIUM_CDC, UNKNOWN}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Kafka Connect, MSK Connect, connector failure, task FAILED, worker rebalance, source connector lag, LagMax, consumer group, sink connector, dead letter queue, DLQ, retry exhaustion, schema registry, Avro, Confluent, Glue Schema Registry, IAM auth, MSK IAM, plugin not found, connector class not found, custom plugin, Debezium, Single Message Transforms, SMT, bootstrap servers, Analytics
  tags: kafka-connect, msk, analytics, troubleshoot, streaming, debezium
---

# Kafka Connect Troubleshooter

## What this skill does

Diagnoses Kafka Connect and Amazon MSK Connect failures by walking a
nine-category decision tree that maps the observed symptom (connector
FAILED, task FAILED, growing source lag, DLQ filling, worker
rebalance storm) to a specific root cause with positive evidence.
The skill is verdict-driven: it never emits a fix without first
producing the failing probe that confirms the cause.

## STRICT output contract

Every invocation MUST emit exactly one diagnostic block per connector
in this shape — no prose before, no commentary after:

```text
TARGET: <connector-name> or <connector-name>/task-<n>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failing category and the probe>
CATEGORY: TASK_EXCEPTION | WORKER_REBALANCE | SOURCE_LAG |
          SINK_DLQ | SINK_RETRY | SCHEMA_REGISTRY | IAM_AUTH |
          PLUGIN_MISSING | CONFIG_ERROR | SMT_ERROR |
          DEBEZIUM_CDC | UNKNOWN
EVIDENCE:
  - <observed symptom — status, trace.state, error message>
  - <failing probe — command and output that confirms the cause>
  - <passing probes — categories ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

A block missing VERDICT, CATEGORY, EVIDENCE, or REMEDIATION is a
contract violation — re-emit the full block. NEVER combine multiple
connectors in a single block.

## Quick navigation

| # | Section | Jump when |
|---|---|---|
| 1 | [STRICT output contract](#strict-output-contract) | Confirm block shape before emitting |
| 2 | [Verdict thresholds](#quick-reference--verdict-thresholds) | Symptom → verdict → category map |
| 3 | [Pre-flight data gate](#pre-flight-data-gate) | Required data sources |
| 4 | [Decision tree](#process--diagnostic-decision-tree) | Step-by-step categories |
| 5 | [NEVER anti-patterns](#never-do-these-things) | Kafka Connect taboos |
| 6 | [Expert heuristic](#expert-heuristic--the-60-second-triage) | 60-second triage |
| 7 | [Recent AWS features](#recent-aws-features-2024-2026) | What changed in 24 months |

## Mindset

A Kafka Connect connector is a stream-processing worker running
inside a Connect cluster. Most failures are not Kafka bugs — they
are configuration drift between the connector, the source system, the
sink system, the schema registry, and the MSK cluster's IAM / network
layer. The skill's job is to find the layer that drifted. The
fastest path is to read connector `status` first (it surfaces the
`trace` exception for failed tasks), then narrow to the category that
matches the symptom signature, then run the category-specific probe.

## Quick reference — verdict thresholds

| Observation | Verdict | Category |
|---|---|---|
| Task `state=FAILED`, `trace` contains exception | **ROOT_CAUSE_FOUND** | TASK_EXCEPTION |
| Logs show repeated `Rebalance` / `JoinGroup` churn | **ROOT_CAUSE_FOUND** | WORKER_REBALANCE |
| LagMax growing, offsets not advancing | **ROOT_CAUSE_FOUND** | SOURCE_LAG |
| DLQ topic receiving records | **ROOT_CAUSE_FOUND** | SINK_DLQ |
| Sink retries exhausted | **ROOT_CAUSE_FOUND** | SINK_RETRY |
| `SchemaRegistryException` / `Connection refused` to registry | **ROOT_CAUSE_FOUND** | SCHEMA_REGISTRY |
| `SASL_NOT_LOGGED_IN` / `Topic authorization failed` on MSK | **ROOT_CAUSE_FOUND** | IAM_AUTH |
| `ClassNotFoundException` on connector startup | **ROOT_CAUSE_FOUND** | PLUGIN_MISSING |
| `Unknown topic` / `bootstrap.servers` wrong | **ROOT_CAUSE_FOUND** | CONFIG_ERROR |
| SMT `Cast` / `ExtractTopic` exception | **ROOT_CAUSE_FOUND** | SMT_ERROR |
| Debezium `snapshot` stuck / `history.internal` unreachable | **ROOT_CAUSE_FOUND** | DEBEZIUM_CDC |
| Logs unavailable (logging disabled) | **NEED_MORE_INFO** | (need logs) |
| AWS Health event for MSK in region | **ESCALATE** | (AWS-side incident) |

## Pre-flight data gate

Kafka Connect diagnosis requires three data sources: connector
status (state, trace, worker_id), CloudWatch Logs excerpt, and the
cluster's bootstrap / IAM configuration.

Data-gathering commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before probing a live connector.

### Data-quality short-circuits

Short-circuit table moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when the input data itself is suspect.

## Process — Diagnostic decision tree (apply in order)

### Step 0: Non-obvious behaviours

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the full gotcha catalog.

### Step 1: Task failure (TASK_EXCEPTION)

**Signature:** `tasks[].state=FAILED`, `trace` contains a Java
exception, OR CloudWatch Logs contain a stack trace.

```bash
jq '.connector.status.tasks[] | select(.state=="FAILED") | {id, trace}' connector-status.json
aws logs filter-log-events \
  --log-group-name /aws/kafkaconnect/my-connector \
  --filter-pattern "Exception" --output json
```

| Exception | Root cause | Fix |
|---|---|---|
| `RetriableCommitFailedException` | Offset commit failed (broker down, auth) | Verify MSK health and IAM. |
| `ConnectException: ..._converter_...` | Converter mismatch | Align `key.converter` / `value.converter` with producer. |
| `InvalidReplicationFactor` | MSK auto-topic-create disabled | Pre-create the topic. |
| `WakeupException` / `InterruptException` | Task interrupted (rebalance) | Route to Step 2. |
| `OutOfMemoryError` | Worker memory pressure | Raise worker capacity or reduce parallel tasks. |
| `SchemaRegistryException` | Registry unreachable | Route to Step 5. |

### Step 2: Worker rebalance storm (WORKER_REBALANCE)

**Signature:** Logs show repeated `JoinGroup` / `SyncGroup` /
`Rebalance` at <5 minute intervals.

```bash
aws logs filter-log-events \
  --log-group-name /aws/kafkaconnect/my-connector \
  --filter-pattern "Rebalance" \
  --start-time $(date -d '1 hour ago' +%s)000 --output json
```

| Observation | Root cause | Fix |
|---|---|---|
| Rebalance every 2-3 min | Heartbeat misses timeout | Raise `session.timeout.ms` to 30000+, `heartbeat.interval.ms` to 9000+. |
| Rebalance after every deploy | Worker over-subscribed | Add worker capacity or split connectors. |
| Rebalance on broker failover | Broker instability | Verify MSK health; check `describe-cluster` State. |
| Rebalance correlates with task restarts | Task OOM loop | Route to Step 1; check for OOM. |
| Two connectors sharing `group.id` | Group coordinator churn | Verify `group.id` uniqueness. |

### Step 3: Source connector lag (SOURCE_LAG)

**Signature:** LagMax grows; source offsets not advancing;
connector `RUNNING` but throughput zero.

| Observation | Root cause | Fix |
|---|---|---|
| Source DB binlog position static | Source DB unreachable / creds wrong | Verify network path and credentials. |
| Consumer group missing from MSK listing | `group.id` wrong | Default is `connect-${connectorName}`. |
| Lag grows linearly, throughput zero | Source throttled (RDS IOPS, CDC limit) | Raise source capacity; check `snapshot.mode`. |
| Lag grows then resets | Consumer kicked out (rebalance loop) | Route to Step 2. |
| Lag on one partition only | Skewed source key (hot key) | Salt the key; add `partition.count`. |
| `offset.storage.topic` missing | Internal offsets lost | Pre-create with correct RF. |

### Step 4: Sink DLQ and retry (SINK_DLQ / SINK_RETRY)

**Signature:** DLQ filling; `errors.retry.timeout` exceeded.

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/KafkaConnect --metric-name ErrorRate \
  --dimensions Name=Connector,Value=my-connector \
  --start-time $(date -d '1 hour ago' -Iseconds) \
  --end-time $(date -Iseconds) --period 60 --statistics Sum
```

| Symptom | Root cause | Fix |
|---|---|---|
| DLQ filling, all records same exception | Sink schema mismatch | Inspect DLQ headers; fix converter or mapping. |
| `errors.retry.timeout` exhausted | Sink throttled | Raise `errors.retry.timeout`; investigate sink capacity. |
| No DLQ configured, task FAILED on first error | DLQ opt-in not set | Add `errors.deadletterqueue.topic.name` + `errors.tolerance=all`. |
| Sink to S3 `AccessDenied` | Connector role lacks s3:PutObject | Add IAM permission. |
| Sink to ES/OS errors on bulk | Buffer too small / cluster throttled | Raise `batch.size`; investigate sink cluster. |

### Step 5: Schema registry (SCHEMA_REGISTRY)

**Signature:** Logs contain `SchemaRegistryException`, `Connection
refused`, `AvroException`, or `Schema not found`.

```bash
# Confluent — reachability test from the worker VPC
curl -s http://<registry-host>:8081/subjects | jq .
# Glue Schema Registry
aws glue get-schema-registry --registry-name my-registry
# Verify the connector's schema registry URL
jq '.connectorConfiguration | map(select(.key=="value.converter.schema.registry.url"))' connector.json
```

| Observation | Root cause | Fix |
|---|---|---|
| `Connection refused` | Worker subnet lacks egress | Add SG egress to registry host/port. |
| `Schema not found` for a subject | Wrong subject name strategy | Verify `value.subject.name.strategy` (default `TopicNameStrategy`). |
| Avro `ConversionException` | Schema incompatible | Check schema compatibility (BACKWARD/FORWARD/NONE). |
| Glue: `AccessDeniedException` | Role lacks `glue:GetSchema*` | Add `glue:GetSchemaVersion` / `GetSchemaByDefinition`. |
| Confluent: `401 Unauthorized` | Auth missing | Add BASIC auth or `schema.registry.basic.auth.*`. |
| Protobuf: `Unsupported format` | Wrong converter | Use `ProtobufConverter` for .proto, not AvroConverter. |

### Step 6: IAM authentication (IAM_AUTH)

**Signature:** Logs contain `SASL_NOT_LOGGED_IN`, `Topic
authorization failed`, or `Cluster authorization failed`.

```bash
jq '.ClusterInfo.ClientAuthentication' auth.json
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111122223333:role/my-connect-role \
  --action-names kafka-cluster:Connect kafka-cluster:DescribeCluster \
                 kafka-cluster:ReadData kafka-cluster:WriteData \
  --resource-arns $CLUSTER_ARN > sim.json
jq '.EvaluationResults[].EvalDecision' sim.json
```

| Observation | Root cause | Fix |
|---|---|---|
| `SASL_NOT_LOGGED_IN` | IAM auth not enabled on MSK | Enable `ClientAuthentication.Sasl.Iam`. |
| `Topic authorization failed` | Policy lacks `WriteData` on topic | Add `kafka-cluster:WriteData` for the topic ARN. |
| ACL auth on IAM-enabled MSK | Mismatched auth method | Use `sasl.iam`; remove `sasl.scram`. |
| SG no egress to brokers on 9094 | SG misconfiguration | Add egress to MSK SG on 9094. |
| `Cluster authorization failed` on DescribeCluster | Missing `DescribeCluster` | Add the action to the role. |

### Step 7: Plugin / connector class not found (PLUGIN_MISSING)

**Signature:** Logs contain `ClassNotFoundException`,
`NoClassDefFoundError`, or connector fails on creation.

```bash
aws kafkaconnect list-custom-plugins --query 'customPlugins[?state==`ACTIVE`]'
jq '.connectorConfiguration | map(select(.key=="connector.class"))' connector.json
aws kafkaconnect describe-custom-plugin --custom-plugin-arn <plugin-arn>
```

| Symptom | Root cause | Fix |
|---|---|---|
| `ClassNotFoundException: io.debezium...MySqlConnector` | Debezium JAR not in plugin | Re-upload a fat JAR with all dependencies. |
| `NoClassDefFoundError: com.fasterxml.jackson...` | Transitive dep missing | Rebuild ZIP with `mvn dependency:copy-dependencies`. |
| Plugin `state=FAILED` | Upload or parsing failed | Re-upload from S3; inspect `describe-custom-plugin`. |
| `Connector class not found` for built-in | Using self-managed class name on MSK | Use MSK's built-in plugin ARN. |
| Two plugins with same `connector.class` | Class conflict | Isolate plugins or remove duplicate. |

### Step 8: Connector configuration errors (CONFIG_ERROR)

**Signature:** Connector fails on creation or restart; error
mentions a config key, topic name, or bootstrap servers.

```bash
# REST API config validation (self-managed)
curl -s http://<worker>:8083/connector-plugins/{class}/config/validate \
  --data @connector-config.json | jq '.validation_results'
jq '.connectorConfiguration' connector.json
```

| Symptom | Root cause | Fix |
|---|---|---|
| `Unknown topic or partition` | `topics` wrong or topic missing | Pre-create the topic or fix the list. |
| `bootstrap.servers` no response | Wrong port or auth mismatch | Use IAM endpoint (9094) for IAM auth. |
| `offset.storage.topic` missing | Default topic not created | Pre-create `connect-offsets`, `connect-configs`, `connect-status`. |
| Converter mismatch | Producer/connector mismatch | Set both converters to match. |
| `tasks.max` > partitions | Idle tasks | Lower `tasks.max` to partition count. |
| Sink `Duplicate key` | Idempotence not configured | Enable sink idempotence (JDBC `insert.mode=upsert`). |

### Step 9: Single Message Transforms (SMT_ERROR)

**Signature:** Logs contain an SMT class (`Cast`, `ExtractTopic`,
`TimestampConverter`) in the exception.

```bash
jq '.connectorConfiguration | map(select(.key | startswith("transforms")))' connector.json
```

| Symptom | Root cause | Fix |
|---|---|---|
| `Cast` on a non-castable field | Cast spec wrong | Inspect schema; cast only primitives. |
| `ExtractTopic` on a nested field | Path wrong | Use `ReplaceField` or flatten first. |
| `TimestampConverter` epoch mismatch | Source format mismatch | Set `target.type` and `field` correctly. |
| `SetSchemaMetadata` schema name mismatch | Schema not registered | Register first, or use matching strategy. |
| SMT order wrong | SMTs run AFTER source converters, BEFORE sink | Reorder the `transforms` list. |
| Custom SMT `ClassNotFoundException` | SMT class not in plugin | Re-build with the custom SMT JAR. |

### Step 10: Debezium CDC specifics (DEBEZIUM_CDC)

**Signature:** Debezium connector (mysql, postgresql, mongodb,
sqlserver); startup hangs or snapshot never completes.

| Symptom | Root cause | Fix |
|---|---|---|
| `history.internal.kafka.topic` producer errors | Topic missing or auth | Pre-create history topic; verify IAM. |
| Snapshot stuck on large table | Single-threaded snapshot | Use `snapshot.fetch.size`; incremental snapshots (1.6+). |
| `binlog` position not found | MySQL purged binlog | Re-snapshot from current; raise binlog retention. |
| Postgres `WAL segment removed` | `wal_level=logical` not set | Set `wal_keep_size`; use `pg_recvlogical`. |
| `slot 'debezium' already exists` | Slot from previous run | Drop the replication slot, or set `slot.name` uniquely. |

### Step 11: AWS-side incident escalation

If AWS Health shows an active MSK or MSK Connect incident in the
region during the failure, emit ESCALATE. Do NOT diagnose connector-
level causes when the platform is degraded.

```bash
aws health describe-events \
  --filter eventStatusCodes=OPEN,services=KAFKA \
  --region us-east-1 --output json
```

### Step 12: Final verdict

- If a single category's failing probe produced positive evidence,
  emit **ROOT_CAUSE_FOUND** with that CATEGORY.
- If two categories overlap (e.g., TASK_EXCEPTION with underlying
  SCHEMA_REGISTRY), pick the **most-specific** category and note the
  task layer in EVIDENCE.
- If a probe requires operator input (logs disabled, REST API
  unreachable), emit **NEED_MORE_INFO** with the data gap.
- If AWS Health shows an active MSK incident, emit **ESCALATE**.

## Output format — worked examples

### Worked example — sink DLQ schema mismatch

```text
TARGET: s3-sink-connector
VERDICT: ROOT_CAUSE_FOUND
REASON: Sink connector sends records to DLQ at 100% error rate. DLQ
  headers show AvroConverter cannot decode — producer uses Protobuf,
  connector is configured with AvroConverter.
CATEGORY: SINK_DLQ
EVIDENCE:
  - connector RUNNING, tasks[0] FAILED then restarted
  - DLQ topic s3-sink-dlq receiving ~200 records/min
  - Failing probe: DLQ header __connect.errors.exception =
    "SerializationException: Error deserializing Avro message";
    producer is Protobuf per producer config
  - Passing probes: no rebalance; IAM valid; topic exists
REMEDIATION:
  1. Change the sink converter to match the producer:
     aws kafkaconnect update-connector --connector-arn $ARN \
       --connector-configuration '{"value.converter":"io.confluent.connect.protobuf.ProtobufConverter",...}'
  2. Verify: aws kafkaconnect describe-connector --connector-arn $ARN
       --query 'connector.state'
  3. Drain the DLQ once the fix is verified.
```

### Worked example — IAM auth missing on MSK

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting an IAM_AUTH verdict.

### Worked example — source lag with hot partition

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting a SOURCE_LAG verdict.

### Worked example — plugin missing (Debezium)

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when formatting a PLUGIN_MISSING verdict.

### Worked example — NEED_MORE_INFO

Moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when logs are unavailable.

## NEVER do these things

- **NEVER restart a connector to "fix" a FAILED task without first
  reading the `trace` and CloudWatch logs.** A restart clears the
  state but not the cause — the connector fails again on the same
  record (sink) or source position. Read the failure first.

- **NEVER assume a connector `RUNNING` state means tasks are
  healthy.** The connector state reflects the framework; tasks may
  all be FAILED. Always inspect `tasks[].state`.

- **NEVER assume Schema Registry is reachable because the operator
  can reach it.** The Connect worker runs in a different network
  context (VPC, subnet, SG). Test from inside the VPC, not from the
  operator's laptop.

- **NEVER use `errors.tolerance=none` (default) for a production sink
  without a DLQ.** The first error stops the task. Set
  `errors.tolerance=all` and configure `errors.deadletterqueue.topic.name`.

- **NEVER run MSK IAM auth with a policy granting `kafka:*` on `*`.**
  Scope to the specific cluster ARN and the specific actions
  (`kafka-cluster:Connect`, `DescribeCluster`, `ReadData`,
  `WriteData`). A broad policy lets any principal with the role
  produce/consume any topic.

- NEVER upload a Debezium plugin as a thin JAR. Debezium connectors
  depend on a dozen transitive libraries; without them the plugin
  throws `NoClassDefFoundError`. Use the official fat JAR / ZIP.

- NEVER use PLAINTEXT (9092) brokers on MSK in production. MSK
  supports TLS (9094) with IAM auth, or SCRAM (9094) with TLS.

- NEVER set `session.timeout.ms` below 10000 on a connector whose
  worker runs GC pauses. A 5-10s GC pause triggers a false rebalance.
  Use 30000 with `heartbeat.interval.ms=9000`.

- NEVER skip the IAM `simulate-principal-policy` check for MSK
  connectors. The execution role MUST have `kafka-cluster:*` on the
  cluster ARN AND on the topic ARNs.

- NEVER combine two connectors with the same `group.id`. They fight
  over the consumer group, triggering a rebalance loop. Default is
  `connect-${connectorName}`; verify uniqueness.

## Expert heuristic — the 60-second triage

When handed a failing Kafka Connect connector and asked "what's
wrong?", run this 60-second triage before deep-diving any single
category:

1. **Pull connector status.** `connector.state` and
   `tasks[].state` narrow the category:
   - `trace` has a Java exception → Step 1 (TASK_EXCEPTION).
   - Logs show `Rebalance` every few minutes → Step 2.
   - State RUNNING but LagMax grows → Step 3 (SOURCE_LAG).
   - DLQ filling → Step 4 (SINK_DLQ / SINK_RETRY).
   - `Connection refused` to schema registry → Step 5.
   - `SASL_NOT_LOGGED_IN` / `authorization failed` → Step 6 (IAM_AUTH).
   - `ClassNotFoundException` on creation → Step 7 (PLUGIN_MISSING).
   - `Unknown topic` / wrong bootstrap → Step 8 (CONFIG_ERROR).
   - SMT class in the trace → Step 9 (SMT_ERROR).
2. **Pull CloudWatch Logs.** The exception is often only in logs.
3. **Verify MSK broker health** (`describe-cluster` `State`=ACTIVE).
4. **Verify IAM** (`simulate-principal-policy` on the connector role).
5. **Verify SG egress** from the worker subnet to MSK on 9094.

If none produces a failing probe, the category is UNKNOWN and the
next step is to enable CloudWatch logging and re-run.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-connector`, `delete-connector`, `create-custom-plugin`,
  `kafka update-configuration`), emit and await operator approval.
- **Never `delete-connector` without first exporting the config.**
  `aws kafkaconnect describe-connector --connector-arn $ARN --output json > backup.json`.
- **Never restart a connector during a rebalance storm.** Wait for
  it to settle, then address the root cause.
- **One category per maintenance window.** Stacking fixes obscures
  which one produced the recovery.
- **Bulk operation safety limit.** Slice a fleet diagnosis into
  batches of at most 3 connectors; emit per-connector REMEDIATION
  and a single CONFIRM per batch.

## Verdict semantics

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `ROOT_CAUSE_FOUND` | A failing probe produced positive evidence. | Primary — terminal for actionable findings. |
| `NEED_MORE_INFO` | A required probe is unavailable (no logs, REST API unreachable). | Pre-decision — emit with the specific data gap. |
| `ESCALATE` | AWS Health shows an active MSK or MSK Connect incident. | Pre-decision — surface event ARN; do NOT diagnose connector-level causes. |

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand to check what changed in the last 24 months.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples moved from this SKILL.md
- [references/error-handling.md](references/error-handling.md) — data-quality short-circuits moved from this SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight data-gathering commands moved from this SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 non-obvious behaviours and recent AWS features moved from this SKILL.md
- [references/msk-connect-config-reference.md](references/msk-connect-config-reference.md) — connector config keys, lifecycle states, and failure modes

## Domain

AWS CloudOps / Analytics — Kafka Connect and MSK Connect failure
diagnosis.

## AWS documentation

- **Amazon MSK Connect Developer Guide** — https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect.html
- **MSK Connect custom plugins** — https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect-custom-plugins.html
- **Amazon MSK IAM access control** — https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control.html
- **Apache Kafka Connect documentation** — https://kafka.apache.org/documentation/#connect
- **Confluent Schema Registry** — https://docs.confluent.io/platform/current/schema-registry/index.html
- **AWS Glue Schema Registry** — https://docs.aws.amazon.com/glue/latest/dg/schema-registry.html
- **Debezium documentation** — https://debezium.io/documentation/
- **Kafka Connect REST API** — https://kafka.apache.org/documentation/#connect_rest
- **AWS Health** — https://health.aws.amazon.com/health/status

