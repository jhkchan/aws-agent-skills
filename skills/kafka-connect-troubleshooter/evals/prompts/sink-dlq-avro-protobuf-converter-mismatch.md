# Eval prompt: sink-dlq-avro-protobuf-converter-mismatch

Diagnose the Kafka Connect / MSK Connect failure. Walk the nine-
category diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, CATEGORY, EVIDENCE, REMEDIATION).

Connector: s3-sink-connector
  (case sink-dlq-avro-protobuf-converter-mismatch)
ConnectorArn: arn:aws:kafkaconnect:us-east-1:111122223333:connector/s3-sink-connector/abc-123
Region: us-east-1

describe-connector output:
  connector.state: RUNNING
  tasks[0].state: FAILED
  tasks[0].trace: ""

CloudWatch Logs (filter-pattern "Exception"):
  org.apache.kafka.common.errors.SerializationException: Error
    deserializing Avro message
  Errors routed to topic s3-sink-dlq at ~200 records/min

DLQ record header __connect.errors.exception:
  "org.apache.kafka.common.errors.SerializationException:
   Error deserializing Avro message for partition 3"

Producer config (verified separately):
  value.converter: io.confluent.connect.protobuf.ProtobufConverter
  value.converter.schema.registry.url: http://registry:8081

Connector config:
  value.converter: io.confluent.connect.avro.AvroConverter
  value.converter.schema.registry.url: http://registry:8081
  errors.tolerance: all
  errors.deadletterqueue.topic.name: s3-sink-dlq

MSK brokers: ACTIVE; consumer group healthy; no rebalance churn.
