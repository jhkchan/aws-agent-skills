# Eval: database-table-scheduled-query

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — database creation, table with memory/magnetic TTL, scheduled query with target table and SNS notification

## Prompt

Create a Timestream database named IoTSensorData in us-east-1.
Create a table TemperatureReadings with memory store TTL of 12
hours and magnetic store TTL of 365 days. Create a scheduled
query named HourlyTemperatureAggregation that aggregates
temperature readings hourly into a target table
HourlyTempAggregates. SNS topic for errors:
arn:aws:sns:us-east-1:123456789012:timestream-errors. Execution
role: arn:aws:iam::123456789012:role/TimestreamSQRole. Tags:
Environment=production, Team=iot.
