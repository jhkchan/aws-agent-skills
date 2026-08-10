# Eval prompt: sfn-vague-report-need-execution-arn

Diagnose the following Step Functions report. Walk the Step 0 signal
check and emit the standard VERDICT block.

## Scenario

A user reports: "my Step Functions workflow is broken, executions keep
failing." They mention the workflow is called `order-pipeline` in
`us-east-1`.

## Known facts

- Workflow name: `order-pipeline`
- Region: `us-east-1`
- No execution ARN provided.
- No error string provided.
- No failing state name provided.
- Workflow type (Standard vs Express) not specified.

## Symptom

The user expects a diagnosis but has provided insufficient identifying
information to walk the decision tree.
