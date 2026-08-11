# Eval: topic-rule-sql-timestream

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — topic rule SQL against payload, Timestream write, republish to alerts, IAM role

## Prompt

Create an IoT topic rule "telemetry-to-timestream" in us-east-1.
SQL: SELECT temperature, humidity, device_id FROM
'device/+/telemetry' WHERE temperature > 30. Actions: write to
Timestream database sensors table telemetry, and republish to
device/alerts. IAM role:
arn:aws:iam::123456789012:role/IoTTopicRuleRole. Error action:
republish to device/errors. Tags: Environment=production.
