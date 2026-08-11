# MSK Connect and Kafka Connect Configuration Reference

This reference catalogues the concrete connector configuration keys,
worker settings, IAM requirements, and CLI shapes used by the
kafka-connect-troubleshooter skill. Each entry includes the key,
default, and known failure modes.

## MSK Connect connector lifecycle states

| State | Meaning | Diagnostic action |
|---|---|---|
| `CREATING` | Provisioning; not yet running | Wait; do NOT diagnose yet. |
| `RUNNING` | Connector framework active | Check `tasks[].state` — tasks may still be FAILED. |
| `CREATING` (long) | Plugin download or worker spin-up slow | Wait ~5-10 min; if stuck, check plugin S3 access. |
| `UPDATING` | Configuration or capacity change in progress | Wait; do NOT diagnose yet. |
| `FAILED` | Connector could not start or recover | Read CloudWatch logs and the connector's `statusDescription`. |
| `DELETING` | Tearing down | Wait; do NOT diagnose. |

## Task states (REST API /describe-connector)

| Task state | Meaning |
|---|---|
| `RUNNING` | Task is processing records. |
| `FAILED` | Task threw an exception; see `trace`. |
| `PAUSED` | Task paused via `pause-connector`. |
| `UNASSIGNED` | Worker has not yet assigned the task (rebalance in progress). |

## Sink connector DLQ and error handling keys

| Key | Default | Effect |
|---|---|---|
| `errors.tolerance` | `none` | `none` = stop on first error. `all` = continue and route to DLQ. |
| `errors.deadletterqueue.topic.name` | (none) | DLQ topic name. Required for DLQ behavior. |
| `errors.deadletterqueue.topic.replication.factor` | `3` | RF for auto-created DLQ topic. |
| `errors.deadletterqueue.context.headers.enable` | `false` | Set `true` to capture the original exception in DLQ record headers. |
| `errors.retry.timeout` | `0` (no retries) | Duration to retry before giving up (ms). |
| `errors.retry.delay.max.ms` | `60000` | Max backoff between retries. |
| `errors.log.enable` | `false` | Set `true` to log each error. |
| `errors.log.include.messages` | `false` | Include the record value in the log. |

**Critical:** For production sinks, always set `errors.tolerance=all`
AND `errors.deadletterqueue.topic.name`. Without both, the first
error stops the task.

## Source connector offset / config / status storage

| Key | Default | Purpose |
|---|---|---|
| `offset.storage.topic` | `connect-offsets` | Source connector offsets (where it left off). |
| `config.storage.topic` | `connect-configs` | Connector configurations. |
| `status.storage.topic` | `connect-statuss` | Connector and task states. |
| `offset.storage.replication.factor` | `3` | RF for offset topic. |
| `config.storage.replication.factor` | `3` | RF for config topic. |
| `status.storage.replication.factor` | `3` | RF for status topic. |

For MSK Connect, these topics MUST exist OR auto-create must be
enabled on MSK. A missing `offset.storage.topic` causes source
connectors to lose position on worker restart.

## Converters (key and value)

| Converter | Use case |
|---|---|
| `org.apache.kafka.connect.storage.StringConverter` | Plain strings (default for keys). |
| `org.apache.kafka.connect.json.JsonConverter` | JSON, with `schemas.enable=true/false`. |
| `io.confluent.connect.avro.AvroConverter` | Avro via Confluent Schema Registry. |
| `io.confluent.connect.protobuf.ProtobufConverter` | Protobuf via Confluent Schema Registry. |
| `com.amazonaws.services.schemaregistry.kafka.connect.avro.AvroConverter` | AWS Glue Schema Registry Avro. |
| `com.amazonaws.services.schemaregistry.kafka.connect.protobuf.ProtobufConverter` | AWS Glue Schema Registry Protobuf. |
| `org.apache.kafka.connect.converters.ByteArrayConverter` | Pass-through raw bytes. |

**Common failure:** `key.converter` set to `StringConverter` while
the producer writes Avro keys. The connector fails on the first
record with a deserialization error.

## Schema Registry URL configuration

| Registry type | Key | Example |
|---|---|---|
| Confluent | `value.converter.schema.registry.url` | `http://registry:8081` |
| Confluent (auth) | `value.converter.basic.auth.credentials.source` | `USER_INFO`, with `value.converter.basic.auth.user.info` |
| Glue | `value.converter.region` | `us-east-1` |
| Glue | `value.converter.registry.name` | `my-registry` |

## MSK IAM auth configuration

**Cluster config (server-side):**
```json
{
  "ClientAuthentication": {
    "Sasl": {"Iam": {"Enabled": true}},
    "Tls": {"CertificateAuthorityArnList": ["<acm-pca-arn>"]}
  }
}
```

**Connector config (client-side):**
```
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.aws.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.aws.iam.IAMClientCallbackHandler
```

**IAM policy (connector execution role):**
```json
{
  "Effect": "Allow",
  "Action": [
    "kafka-cluster:Connect",
    "kafka-cluster:DescribeCluster"
  ],
  "Resource": "arn:aws:kafka:us-east-1:111122223333:cluster/my-msk/abc"
},
{
  "Effect": "Allow",
  "Action": [
    "kafka-cluster:ReadData",
    "kafka-cluster:WriteData"
  ],
  "Resource": [
    "arn:aws:kafka:us-east-1:111122223333:topic/my-msk/abc/my-topic-*"
  ]
}
```

## Worker rebalance parameters

| Key | Default | Recommended | Trade-off |
|---|---|---|---|
| `session.timeout.ms` | `10000` | `30000` | Lower = faster failure detection, more false rebalances. |
| `heartbeat.interval.ms` | `3000` | `9000` | Should be ~1/3 of `session.timeout.ms`. |
| `max.poll.interval.ms` | `300000` | `600000` | Lower = task killed if processing is slow. |
| `partition.assignment.strategy` | `RangeAssignor` | `CooperativeStickyAssignor` | Cooperative reduces rebalance churn. |

## Common Debezium connector keys

| Key | Purpose |
|---|---|
| `database.hostname`, `database.port`, `database.user`, `database.password` | Source DB connection. |
| `database.server.name` | Logical name for the source (namespace). |
| `history.internal.kafka.topic` | DB schema history topic (Debezium 2.x). |
| `history.internal.kafka.bootstrap.servers` | Brokers for the history topic. |
| `snapshot.mode` | `initial`, `schema_only`, `never`, `initial_only`. |
| `signal.data.collection` | Signaling table for incremental snapshots (Debezium 1.6+). |

**Critical:** `history.internal.kafka.topic` must exist and the
connector role must have produce/consume permissions. Without it,
Debezium fails on startup with a producer error.
