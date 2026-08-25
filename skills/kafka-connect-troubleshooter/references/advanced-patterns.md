# Advanced patterns — kafka-connect-troubleshooter

Step-0 non-obvious behaviours and recent AWS features, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Step 0: Non-obvious behaviours (moved from SKILL.md)

- **Task `trace` is frequently empty even when the task threw.** MSK
  Connect sometimes returns empty trace; the exception is only in
  CloudWatch Logs. Always check both.
- **A connector can be `RUNNING` while all its tasks are `FAILED`.**
  Connector state reflects the framework; task state reflects the
  actual work. Always inspect `tasks[].state`.
- **Worker rebalance is normal on deploy; pathological on a 5-min
  cadence.** Every 30+ min is fine. Every 2-5 min is a
  `session.timeout.ms` / heartbeat mismatch or over-subscribed worker.
- **Source LagMax is a consumer-group metric, not a connector
  metric.** The source connector creates a consumer group (often
  `connect-${connectorName}`); if the group is missing, `group.id`
  is wrong.
- **Sink DLQ is opt-in.** Without `errors.deadletterqueue.topic.name`
  and `errors.tolerance=all`, errors stop the task. A failed sink
  task with no DLQ is default behavior, not a bug.
- **Schema registry URL must be reachable from the Connect worker,
  not the operator.** For MSK Connect, the registry (Confluent,
  Glue, Apicurio) must be reachable from the worker VPC.
- **MSK IAM auth requires `kafka-cluster` resource in the policy.**
  Must grant `kafka-cluster:Connect`, `DescribeCluster`, `ReadData`,
  `WriteData` on the cluster ARN. `kafka:*` on `*` is insufficient
  if the ARN does not match.
- **MSK Connect custom plugin must be uploaded to S3 first.** A
  `ClassNotFoundException` on a Debezium connector usually means the
  plugin was uploaded without all transitive dependencies (Debezium
  bundles are fat JARs).
- **Converters must match on key and value.** A common error:
  `value.converter=AvroConverter` but
  `key.converter=StringConverter`. If the producer writes Avro keys,
  the connector fails on the first record.
- **Debezium `history.internal.kafka.topic` must exist.** Debezium
  stores DB schema history in a Kafka topic; if the connector cannot
  produce to it, it fails on startup.
- **MSK Connect workers have a fixed set of SGs and subnets.** The
  connector inherits these from the worker config; you cannot
  override per-connector.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **MSK Connect custom plugins (2024-2025):** `create-custom-plugin`
  now supports ZIP archives up to 50 MB. Debezium 2.x and 3.x bundles
  are supported. Lifecycle: `CREATING` → `ACTIVE` → (optionally)
  `FAILED`.
- **Debezium 2.5+ on MSK Connect (2024-2025):** Incremental snapshot
  via `signal.data.collection`; improved PostgreSQL logical
  replication slot handling; new MongoDB source connector.
- **MSK Connect capacity auto-scaling (2024-2025):** Worker capacity
  can auto-scale on CPU utilization. Reduces over-provisioning.
- **MSK IAM auth v2 (2024-2025):** Stricter policy evaluation —
  `kafka-cluster:WriteDataIdempotently` and
  `DescribeClusterDynamicConfiguration` are separate actions. Update
  IAM policies if the connector uses idempotent producers.
- **SMT predicates (2024-2025):** Connect 3.x supports `predicates`
  on SMTs, allowing conditional transforms (e.g., apply `Cast` only
  if topic matches a regex).
- **MSK Tiered Storage (2024-2025):** Topic data offloaded to S3.
  Source connectors reading tiered topics must use a broker that
  supports tiered fetch.
- **CloudWatch Logs for MSK Connect (2024-2025):** Log delivery to
  CloudWatch, S3, or Firehose is now connector-level. Always enable
  `workerLogDelivery.cloudWatchLogs.enabled=true` on production.
