# Diagnostic commands — kafka-connect-troubleshooter

Pre-flight data-gathering commands, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Pre-flight data-gathering commands (moved from SKILL.md)

```bash
# 1. Connector status (MSK Connect)
CONNECTOR_ARN=arn:aws:kafkaconnect:us-east-1:111122223333:connector/my-connector/abc-123
aws kafkaconnect describe-connector --connector-arn $CONNECTOR_ARN \
  --output json > connector.json
# OR via REST API (self-managed)
curl -s http://<connect-worker>:8083/connectors/my-connector/status | jq .

# 2. CloudWatch Logs
aws logs filter-log-events \
  --log-group-name /aws/kafkaconnect/my-connector \
  --filter-pattern "ERROR" --output json > connector-errors.json

# 3. MSK cluster bootstrap and auth
aws kafka get-bootstrap-brokers --cluster-arn $CLUSTER_ARN > bootstrap.json
aws kafka describe-cluster --cluster-arn $CLUSTER_ARN \
  --query 'ClusterInfo.ClientAuthentication' > auth.json
```
