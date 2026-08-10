# Baseline (no-skill) response: distributed-map-s3-batch

This file captures what a generic assistant produces WITHOUT the
stepfunctions-statemachine-deployer skill loaded — the contrast that
proves the skill surfaces Distributed Map specifics (ItemReader,
ItemBatcher, ToleratedFailurePercentage, separate child executions,
correct IAM for S3 reads).

---

Sure, here's a Step Functions workflow with a Map state that processes
your CSV.

```json
{
  "StartAt": "ProcessLargeDataset",
  "States": {
    "ProcessLargeDataset": {
      "Type": "Map",
      "ItemsPath": "$.items",
      "Iterator": {
        "StartAt": "ProcessBatch",
        "States": {
          "ProcessBatch": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": { "FunctionName": "ProcessBatchFn" },
            "End": true
          }
        }
      },
      "Next": "Summarize"
    },
    "Summarize": { "Type": "Succeed" }
  }
}
```

You'll need to read the CSV file from S3 first and pass the items into
the Map state's input. Try using a Lambda to read the file, or just load
it inline before the workflow runs.

Deploy with:

```
aws stepfunctions create-state-machine --name etl-pipeline \
  --definition file://def.json \
  --role-arn arn:aws:iam::111111111111:role/etl-sfn-role
```
