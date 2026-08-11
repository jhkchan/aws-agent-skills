# Baseline (no-skill) — sql-session-windows

> This is the response a model produces **without** the skill definition.
> It creates the SQL application but omits the InputSchema columns, uses
> a hopping window instead of SESSION(), skips the destination output
> configuration, and does not configure CloudWatch logging. The pump
> fails because DESTINATION_SQL_STREAM is never declared.

---

Here are the commands to deploy your Kinesis Data Analytics SQL
application:

```bash
aws kinesisanalyticsv2 create-application \
  --application-name session-windows-sql \
  --runtime-environment SQL-1_0 \
  --service-execution-role arn:aws:iam::123456789012:role/KDAExecutionRole \
  --application-configuration '{
    "SqlApplicationConfiguration": {
      "Inputs": [{
        "NamePrefix": "SOURCE_SQL_STREAM",
        "KinesisStreamsInput": {
          "ResourceARN": "arn:aws:kinesis:us-east-1:123456789012:stream/clicks",
          "RoleARN": "arn:aws:iam::123456789012:role/KDAExecutionRole"
        },
        "InputSchema": {
          "RecordFormat": {"RecordFormatType": "JSON"}
        }
      }]
    },
    "ApplicationCodeConfiguration": {
      "CodeContent": {
        "TextInput": "CREATE OR REPLACE PUMP AS INSERT INTO DESTINATION_SQL_STREAM SELECT STREAM user_id, COUNT(*) FROM SOURCE_SQL_STREAM_001 GROUP BY user_id, FLOOR(ROWTIME TO MINUTE);"
      }
    }
  }'

aws kinesisanalyticsv2 start-application --application-name session-windows-sql
```

Your SQL app should run once started.
