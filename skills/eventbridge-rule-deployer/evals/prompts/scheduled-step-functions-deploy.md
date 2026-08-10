# Eval prompt: scheduled-step-functions-deploy

Design an EventBridge scheduled rule deployment for the following
scenario. Emit the standard PLAN block (RULE, TARGETS, RETRY, DLQ,
INPUT_TRANSFORM, PREREQUISITES, VERDICT, GAP, TEMPLATE).

Design reference: scheduled-step-functions-deploy
Account: 111111111111
Region: us-east-1

Schedule: nightly at 02:00 UTC
Target: Step Functions state machine `nightly-reconciliation`
  ARN: arn:aws:states:us-east-1:111111111111:stateMachine:nightly-reconciliation
DLQ: arn:aws:sqs:us-east-1:111111111111:eventbridge-nightly-recon-dlq
  (created with 14-day retention).
Step Functions role trusts events.amazonaws.com and grants
states:StartExecution.

The Step Functions workflow handles its own internal retries, so
the EventBridge retry policy should be bounded.
