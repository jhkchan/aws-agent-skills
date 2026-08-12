# End-to-End Example: Step Functions Distributed Map State Deployment

A walkthrough showing how to use the `stepfunctions-map-state-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a Distributed Map state that reads a CSV file
from S3, processes rows in batches of 100, and tolerates up to 5%
batch failures. The Map state needs:

- Map type: Distributed
- S3 input: s3://my-data-bucket/datasets/records.csv (CSV, first row headers)
- ItemBatchSize: 100
- MaxConcurrency: 50
- ToleratedFailurePercentage: 5
- Lambda function: process-row
- Max items: 10000
- Tags: Environment=production

---

## Step 1 — Invoke the skill

### Option A: Natural language

```
You: "Create a Step Functions Distributed Map state named
      ProcessRecords that reads a CSV file from
      s3://my-data-bucket/datasets/records.csv. Process in batches
      of 100 with MaxConcurrency 50. Allow 5% failure rate. Lambda
      function process-row handles each row."
```

### Option B: CLI routing

```bash
node cli/bin/cli.js route "step functions distributed map s3 csv"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
MAP_STATE: ProcessRecords (DISTRIBUTED)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Map type: Distributed
  [✓] ItemProcessor: defined (Mode: DISTRIBUTED, ExecutionType: STANDARD)
  [✓] ItemsPath: N/A (S3 input via ItemReader)
  [✓] MaxConcurrency: 50
  [✓] MaxItems: 10000
  [✓] ItemBatchSize: 100 (100 items per child execution → 100 child executions max)
  [✓] ToleratedFailurePercentage: 5 (allows up to 5% batch failures)
  [✓] S3 input: s3://my-data-bucket/datasets/records.csv (CSV, FIRST_ROW headers)
  [✓] ResultSelector: { "processed.$": "$" }
  [✓] ResultPath: $.processing_result
  [✓] Error handling: Retry (3 attempts, exponential backoff) + Catch → HandleError
  [✓] IAM role: has s3:GetObject on my-data-bucket
  [✓] Item count: 8500 rows (within Distributed 10000 limit)
  [✓] Tags: Environment=production, Workflow=data-pipeline
VERIFICATION_COMMANDS:
  aws stepfunctions describe-state-machine --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:DataPipeline
  aws stepfunctions describe-execution --execution-arn <execution-arn>
```

---

## Step 3 — ASL definition

```json
{
  "StartAt": "ProcessRecords",
  "States": {
    "ProcessRecords": {
      "Type": "Map",
      "MaxConcurrency": 50,
      "MaxItems": 10000,
      "ItemBatchSize": 100,
      "ToleratedFailurePercentage": 5,
      "Label": "data-pipeline-batch",
      "ItemReader": {
        "Resource": "arn:aws:states:::s3:getObject",
        "ReaderConfig": {
          "InputType": "CSV",
          "CSVHeaderLocation": "FIRST_ROW"
        },
        "Parameters": {
          "Bucket": "my-data-bucket",
          "Key": "datasets/records.csv"
        }
      },
      "ItemProcessor": {
        "ProcessorConfig": {
          "Mode": "DISTRIBUTED",
          "ExecutionType": "STANDARD"
        },
        "StartAt": "ProcessRow",
        "States": {
          "ProcessRow": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-row",
            "Retry": [
              {
                "ErrorEquals": ["States.TaskFailed"],
                "IntervalSeconds": 2,
                "MaxAttempts": 3,
                "BackoffRate": 2.0
              }
            ],
            "Catch": [
              {
                "ErrorEquals": ["States.ALL"],
                "Next": "HandleError",
                "ResultPath": "$.error"
              }
            ],
            "End": true
          },
          "HandleError": {
            "Type": "Fail",
            "Error": "BatchProcessingFailed"
          }
        }
      },
      "ResultSelector": {
        "processed_count.$": "$.length(@)",
        "items.$": "$"
      },
      "ResultPath": "$.processing_result",
      "Next": "NotifyComplete"
    },
    "NotifyComplete": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:notify",
      "End": true
    }
  }
}
```

---

## Step 4 — IAM policy for the state machine role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-row"
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-data-bucket/datasets/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "states:StartExecution",
        "states:DescribeExecution",
        "states:StopExecution"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Step 5 — Deploy and verify

```bash
# Create the state machine
SM_ARN=$(aws stepfunctions create-state-machine \
  --name "DataPipeline" \
  --definition file://definition.json \
  --role-arn arn:aws:iam::123456789012:role/StepFunctionsRole \
  --query 'stateMachineArn' --output text)

# Start an execution
EXEC_ARN=$(aws stepfunctions start-execution \
  --state-machine-arn "$SM_ARN" \
  --input '{}' \
  --query 'executionArn' --output text)

# Verify the execution (Map state spawns child executions)
aws stepfunctions describe-execution --execution-arn "$EXEC_ARN"
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| ItemProcessor vs Iterator | Uses Iterator | Uses ItemProcessor with Mode DISTRIBUTED | Iterator forces Inline; Distributed requires ItemProcessor |
| ItemBatchSize | Not set (default 1) | Set to 100 | Reduces child executions by 100x; major cost saver |
| ToleratedFailurePercentage | Not set (default 0) | Set to 5 | Without this, one batch failure fails entire Map |
| S3 IAM permission | Not checked | s3:GetObject on target bucket | Map fails at runtime without S3 read access |
| MaxItems | Not set | Set to 10000 | Hard cap prevents processing beyond limit |
| Label | Not set | Set to data-pipeline-batch | Makes child executions identifiable for debugging |

---

## Related artifacts

- **Skill definition:** `skills/stepfunctions-map-state-deployer/SKILL.md`
- **Map configuration guide:** `skills/stepfunctions-map-state-deployer/references/map-configuration-and-batching.md`
- **Distributed Map and S3 guide:** `skills/stepfunctions-map-state-deployer/references/distributed-map-and-s3.md`
- **Eval suite:** `skills/stepfunctions-map-state-deployer/evals/evals.json`
- **Legacy test cases:** `skills/stepfunctions-map-state-deployer/eval/test-cases.yaml`
