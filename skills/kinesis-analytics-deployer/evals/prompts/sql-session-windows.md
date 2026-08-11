# Eval: sql-session-windows

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SQL runtime, session windows, Kinesis source and destination

## Prompt

Deploy a production Kinesis Data Analytics SQL application named
"session-windows-sql" in us-east-1. Runtime environment
SQL-1_0. Service execution role KDAExecutionRole with Kinesis
GetRecords on stream clicks, Kinesis PutRecord on stream
sessions-out, CloudWatch Logs on
/aws/kinesis-analytics/session-windows-sql. Source: Kinesis Data
Stream clicks (ACTIVE), JSON record format, columns event_time
(TIMESTAMP), user_id (VARCHAR(64)), event_type (VARCHAR(32)).
Starting position NOW. Destination: Kinesis Data Stream
sessions-out. Application code: session window pump using
SESSION(event_time, INTERVAL '60' SECONDS) grouping by user_id
with COUNT(*) aggregate. CloudWatch log group
/aws/kinesis-analytics/session-windows-sql. Account: 123456789012.
