# Eval prompt: syntax-error-command-ordering

Diagnose the following CloudWatch Logs Insights failure. Walk the
SYNTAX_ERROR diagnostic tree and emit the standard VERDICT block.

## Scenario

A user runs a Logs Insights query on log group
`/aws/lambda/order-processor` and the query fails with a syntax
error.

## Known facts

- Query text:
  ```
  fields @timestamp, @message
  | limit 10
  | sort @timestamp desc
  ```
- Error message: `Unexpected token 'sort' — limit must be the last
  command in the query`
- Time range: last 1 hour
- The log group has data and previous queries (without the ordering
  issue) returned results

## Symptom

The query status is `Failed`. The error message explicitly cites the
`sort` command appearing after `limit`.
