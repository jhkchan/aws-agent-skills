# Eval prompt: contributor-insights-not-enabled

Diagnose the following CloudWatch Logs Insights / Contributor Insights
failure. Walk the CONTRIBUTOR_INSIGHTS diagnostic tree and emit the
standard VERDICT block.

## Scenario

A user enabled Logs Insights on log group `/aws/vpc/flow-logs` and
expected Contributor Insights to show data automatically. The
Contributor Insights tab is empty.

## Known facts

- Log group: `/aws/vpc/flow-logs`
- The user has been running Logs Insights queries successfully
- `aws logs describe-contributor-insights --log-group-name
  /aws/vpc/flow-logs` returns an empty response (no rules found)
- `aws logs describe-contributor-insights` (listing all rules) shows
  rules for other log groups but NOT for `/aws/vpc/flow-logs`
- VPC Flow Logs are actively ingesting (lastIngestionTime is recent)
- The user says: "I enabled Logs Insights so Contributor Insights
  should work too, right?"

## Symptom

The Contributor Insights tab for `/aws/vpc/flow-logs` is completely
empty — no rules, no data, no graphs.
