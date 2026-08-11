# Eval prompt: plugin-missing-debezium-class-not-found

Diagnose the Kafka Connect / MSK Connect failure. Walk the nine-
category diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, CATEGORY, EVIDENCE, REMEDIATION).

Connector: debezium-mysql-source
  (case plugin-missing-debezium-class-not-found)
ConnectorArn: arn:aws:kafkaconnect:us-east-1:111122223333:connector/debezium-mysql-source/ghi-789
Region: us-east-1

describe-connector output:
  connector.state: FAILED
  tasks: none (no tasks created)
  statusDescription: "Connector class instantiation failed"

CloudWatch Logs (filter-pattern "ClassNotFoundException"):
  java.lang.ClassNotFoundException:
    io.debezium.connector.mysql.MySqlConnector

describe-custom-plugin (the referenced plugin ARN):
  state: FAILED
  failureDescription: "missing manifest dependencies"

Connector config:
  connector.class: io.debezium.connector.mysql.MySqlConnector
  plugin.arn: arn:aws:kafkaconnect:us-east-1:111122223333:custom-plugin/debezium-thin/xyz

MSK reachable; IAM valid; source DB reachable from the worker subnet.
