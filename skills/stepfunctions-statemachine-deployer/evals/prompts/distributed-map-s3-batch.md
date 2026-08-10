# Eval prompt: distributed-map-s3-batch

Design a deployment plan for an AWS Step Functions Standard state machine
that uses a Distributed Map to process a large CSV file. Emit the standard
VERDICT block (STATE_MACHINE_SPEC, VERDICT, ARCHITECTURE, CHECKLIST,
FINDINGS, DEPLOY_COMMANDS).

## Requirements

- Name: `etl-pipeline`
- Region: us-east-1
- Account: 111111111111
- Type: STANDARD
- Workflow:
  1. `ProcessLargeDataset` — Distributed Map reading from S3
     (`s3://my-dataset/input/2026-08.csv`, ~10M rows CSV)
  2. The Map's Iterator invokes Lambda `ProcessBatchFn` (timeout 300s)
  3. Terminal: `Summarize` → Succeed
- Distributed Map config:
  - `MaxConcurrency`: 1000
  - `ItemReader.Resource`: `arn:aws:states:::s3:getObject` with
    `ReaderConfig.InputType: CSV` and `CSVHeaderLocation: FIRST_ROW`
  - `ItemBatcher.MaxItemsPerBatch`: 500
  - `ToleratedFailurePercentage`: 0.5
  - Each iteration has Retry on `Lambda.ServiceException` (5 attempts, 5s,
    2.0 backoff) and Catch on `States.ALL` → `BatchFail`.
- Execution role: `etl-sfn-role` exists with trust for
  `states.amazonaws.com`, with `s3:GetObject` on `my-dataset` bucket,
  `lambda:InvokeFunction` on `ProcessBatchFn`, and DynamoDB access
  already in place for the summarize step.

Output the complete deployment plan including the Distributed Map ASL
definition and the IAM identity policy derivation.
