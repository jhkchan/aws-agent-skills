# Eval prompt: pipes-enrichment-pipeline

Design an EventBridge Pipes workflow for the following scenario.
Emit the standard ARCHITECTURE block (BUS, PATTERN, TARGETS,
RETRY, SAFETY, AUDIT, VERDICT, TEMPLATE). Include the create-pipe
CLI with the filter pattern on status=PAID.

Design reference: pipes-enrichment-pipeline
Account: 111111111111
Region: us-east-1

Source: DynamoDB Streams on table Orders (status transitions to
PAID). Stream ARN:
  arn:aws:dynamodb:us-east-1:111111111111:table/Orders/stream/2026-08-01
Enrichment: Lambda enrich-order (calls pricing service, adds fields)
Target: Step Functions state machine order-flow
  (arn:aws:states:us-east-1:111111111111:stateMachine:order-flow)
Role ARN: arn:aws:iam::111111111111:role/service-role/EventBridge-Pipe-Role
  (already created with DynamoDB Streams read + SFN StartExecution).
