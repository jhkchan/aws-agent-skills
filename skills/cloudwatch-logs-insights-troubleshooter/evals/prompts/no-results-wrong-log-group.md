# Eval prompt: no-results-wrong-log-group

Diagnose the following CloudWatch Logs Insights failure. Walk the
NO_RESULTS diagnostic tree and emit the standard VERDICT block
(INCIDENT, VERDICT, ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A user runs a Logs Insights query on log group `/aws/lambda/my-api`
and gets 0 rows back.

## Known facts

- Query text:
  ```
  fields @timestamp, @message
  | filter @message like /ERROR/
  | limit 100
  ```
- Time range: last 15 minutes
- `aws logs describe-log-groups --log-group-name-prefix /aws/lambda/my-api`
  returns two groups:
  - `/aws/lambda/my-api` (storedBytes: 12 MB, very old)
  - `/aws/lambda/my-api-prod` (storedBytes: 4.2 GB, active)
- `aws logs describe-log-streams --log-group-name /aws/lambda/my-api
  --order-by LastEventTime --descending --limit 1` returns:
  - `lastIngestionTime`: 2025-03-01T14:22:00Z (months ago)
- `aws logs describe-log-streams --log-group-name
  /aws/lambda/my-api-prod --order-by LastEventTime --descending
  --limit 1` returns:
  - `lastIngestionTime`: 2 minutes ago
- The user confirms the application is running and logging errors.

## Symptom

The query completes successfully (status: Complete) but the results
array is empty `[]`.
