# Eval prompt: timeout-no-early-filter

Diagnose the following CloudWatch Logs Insights failure. Walk the
TIMEOUT diagnostic tree and emit the standard VERDICT block.

## Scenario

A user runs a Logs Insights query on log group `/ecs/prod-app` and
the query is cancelled (timeout).

## Known facts

- Query text:
  ```
  fields @timestamp, level, msg
  | parse @message "* * *" as ts, level, msg
  | sort @timestamp desc
  | limit 1000
  ```
- Time range: last 7 days
- `aws logs describe-queries --log-group-name /ecs/prod-app --status
  Cancelled` shows this query with status `Cancelled`
- CloudWatch metric `IncomingBytes` for this log group shows
  approximately 50 GB/day (350 GB total for the 7-day window)
- There is no `filter` command anywhere in the query
- `parse` runs on every event before `sort`

## Symptom

The query status is `Cancelled` after running for several minutes.
