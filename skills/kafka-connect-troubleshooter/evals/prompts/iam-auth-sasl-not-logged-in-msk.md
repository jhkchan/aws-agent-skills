# Eval prompt: iam-auth-sasl-not-logged-in-msk

Diagnose the Kafka Connect / MSK Connect failure. Walk the nine-
category diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, CATEGORY, EVIDENCE, REMEDIATION).

Connector: postgres-source-connector
  (case iam-auth-sasl-not-logged-in-msk)
ConnectorArn: arn:aws:kafkaconnect:us-east-1:111122223333:connector/postgres-source-connector/def-456
ClusterArn: arn:aws:kafka:us-east-1:111122223333:cluster/my-msk/abc-999
Region: us-east-1

describe-connector output:
  connector.state: FAILED
  tasks[0].state: FAILED

CloudWatch Logs:
  "ClusterAuthorizationException: SASL_NOT_LOGGED_IN"
  "Error while fetching metadata with correlation id 42"

MSK describe-cluster ClientAuthentication.Sasl:
  returns {} (Iam.enabled: false; only Scram enabled)

Connector config:
  security.protocol: SASL_SSL
  sasl.mechanism: AWS_MSK_IAM

Connector execution role IAM simulate-principal-policy:
  kafka-cluster:Connect on cluster ARN: allowed
  kafka-cluster:ReadData on topic ARNs: allowed
  kafka-cluster:WriteData on topic ARNs: allowed

Worker SG egress: port 9094 to MSK SG (verified)
