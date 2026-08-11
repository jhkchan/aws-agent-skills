# Eval prompt: schema-registry-connection-refused-vpc

Diagnose the Kafka Connect / MSK Connect failure. Walk the nine-
category diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, CATEGORY, EVIDENCE, REMEDIATION).

Connector: jdbc-sink-connector
  (case schema-registry-connection-refused-vpc)
Region: us-east-1
Worker subnet: subnet-private-1a, SG sg-worker-123

describe-connector output:
  connector.state: FAILED
  tasks[0].state: FAILED
  tasks[0].trace: "io.confluent.common.config.ConfigException:
    Missing schema registry url"

CloudWatch Logs:
  "io.confluent.kafka.schemaregistry.client.rest.exceptions
   .RestClientException: Connection refused"
  "SchemaRegistryException: Could not find schema"

Connector config:
  value.converter: io.confluent.connect.avro.AvroConverter
  value.converter.schema.registry.url: http://10.50.10.20:8081

Worker SG (sg-worker-123) egress rules:
  - 0.0.0.0/0 port 443 (HTTPS)
  - MSK SG on port 9094
  (NO rule for the registry host 10.50.10.20 on port 8081)

Operator verification:
  curl http://10.50.10.20:8081/subjects from laptop
  → returns the subjects list (200 OK)
