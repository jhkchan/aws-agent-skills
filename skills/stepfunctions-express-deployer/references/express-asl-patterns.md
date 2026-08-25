# Express-Compatible ASL Patterns — Step Functions Express Deployer

Reference ASL patterns for Express Workflows: Distributed Map,
Inline Map, `.sync` integration, AWS SDK integration, idempotency,
error handling, and EventBridge-scheduled invocation. Substitute
`<REGION>`, `<ACCOUNT>`, `<FS_ID>`, `<NAME>`, `<RULE_NAME>`,
`<ROLE_ARN>`, `<FUNCTION_ARN>`, `<BUCKET>`, `<KEY>` as needed.
Stored here so the main skill body stays scannable; see the 9-step
procedure for when to apply each variant.

## 1. Distributed Map on Express (with S3 ItemReader)

Distributed Map is supported on Express, but the total iteration
time MUST fit in the 5-min cap. Use `MaxConcurrency` 1000 with
short per-item Lambdas; monitor `MapRunItemCount` and
`MapRunFailedCount`.

```json
{
  "StartAt": "FanOut",
  "States": {
    "FanOut": {
      "Type": "Map",
      "ItemProcessor": {
        "ProcessorConfig": { "Mode": "DISTRIBUTED" },
        "StartAt": "ProcessItem",
        "States": {
          "ProcessItem": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:process-item",
            "End": true
          }
        }
      },
      "ItemReader": {
        "Resource": "arn:aws:states:::s3:getObject",
        "Parameters": { "Bucket": "<BUCKET>", "Key": "<KEY>" }
      },
      "MaxConcurrency": 1000,
      "End": true
    }
  }
}
```

For large fan-outs, the child execution ARNs appear in the
`MapRun` resource in CloudWatch Metrics. Alarm on
`MapRunFailedCount` > 0.

## 2. Inline Map on Express (≤ 40 concurrent)

Inline Map runs within the parent execution; concurrency is capped
at 40. The parent execution's state counts toward the 5-min cap.

```json
{
  "StartAt": "Inline",
  "States": {
    "Inline": {
      "Type": "Map",
      "ItemsPath": "$.items",
      "MaxConcurrency": 40,
      "Iterator": {
        "StartAt": "Handle",
        "States": {
          "Handle": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:handle",
            "End": true
          }
        }
      },
      "End": true
    }
  }
}
```

## 3. .sync integration (run-job-and-wait, Express-compatible)

`.sync` is supported on Express for run-job integrations (Glue,
Batch, ECS, SageMaker, Comprehend). The state blocks until the
underlying job completes — the wait time counts toward the 5-min
cap.

```json
{
  "StartAt": "RunGlueJob",
  "States": {
    "RunGlueJob": {
      "Type": "Task",
      "Resource": "arn:aws:states:::glue:startJobRun.sync",
      "Parameters": {
        "JobName": "my-etl-job",
        "Arguments": { "--input_path.$": "$.input" }
      },
      "End": true
    }
  }
}
```

`.waitForTaskToken` is NOT supported on Express — it would require
unbounded wait. Replace with `.sync` or migrate to STANDARD.

## 4. AWS SDK integration (direct API call, no Lambda)

Express supports AWS SDK integrations for direct API calls without
a Lambda wrapper. The IAM execution role MUST allow the underlying
SDK action (e.g., `dynamodb:UpdateItem`, not `lambda:*`).

```json
{
  "StartAt": "UpdateDynamoDB",
  "States": {
    "UpdateDynamoDB": {
      "Type": "Task",
      "Resource": "arn:aws:states:::dynamodb:updateItem",
      "Parameters": {
        "TableName": "IdempotencyTable",
        "Key": { "id": { "S.$": "$$.Execution.Id" } },
        "UpdateExpression": "SET #s = :s",
        "ExpressionAttributeNames": { "#s": "status" },
        "ExpressionAttributeValues": { ":s": { "S": "completed" } }
      },
      "End": true
    }
  }
}
```

## 5. Idempotency pattern for at-least-once delivery

Express executions are at-least-once. Side-effecting integrations
MUST have an idempotency key persisted BEFORE the side effect.

```json
{
  "StartAt": "RecordIdempotencyKey",
  "States": {
    "RecordIdempotencyKey": {
      "Type": "Task",
      "Resource": "arn:aws:states:::dynamodb:putItem",
      "Parameters": {
        "TableName": "IdempotencyTable",
        "Item": {
          "id": { "S.$": "$$.Execution.Id" },
          "status": { "S": "pending" }
        },
        "ConditionExpression": "attribute_not_exists(id)"
      },
      "Next": "ChargeCard"
    },
    "ChargeCard": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:charge-card",
      "Parameters": {
        "IdempotencyKey.$": "$$.Execution.Id",
        "Amount.$": "$.amount"
      },
      "Retry": [{ "ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 3 }],
      "End": true
    }
  }
}
```

`ConditionExpression: attribute_not_exists(id)` ensures only the
first execution writes the key; duplicate retries on the same input
fail at the `RecordIdempotencyKey` state with
`DynamoDB.ConditionalCheckFailedException`, which Step Functions
treats as a no-op (catch and Succeed).

## 6. Error handling with Retry and Catch

```json
{
  "ChargeCard": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:charge-card",
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
        "Next": "CompensatingAction",
        "ResultPath": "$.error"
      }
    ],
    "End": true
  },
  "CompensatingAction": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:refund",
    "End": true
  }
}
```

For Express, total retry duration MUST fit in the 5-min cap.
Compute `MaxAttempts * IntervalSeconds * BackoffRate^MaxAttempts`
and verify it fits.

## 7. EventBridge-scheduled Express execution

The EventBridge rule uses a schedule expression; the target is the
Express state machine with a role that trusts
`events.amazonaws.com`.

```bash
aws events put-rule --name <RULE_NAME> \
  --schedule-expression "rate(5 minutes)"

aws events put-targets --rule <RULE_NAME> \
  --targets 'Id=1,Arn=arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME>,RoleArn=<ROLE_ARN>'
```

The target role policy MUST allow `states:StartExecution` on the
state machine ARN:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "states:StartExecution",
    "Resource": "arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME>"
  }]
}
```

## 8. Sync invocation from API Gateway

API Gateway invokes Express sync via the Step Functions integration
with `RequestResponse`. Set the API Gateway integration timeout to
29000 ms (the maximum) to avoid 504s when Express finishes near the
30s mark.

```json
{
  "x-amazon-apigateway-integration": {
    "uri": "arn:aws:apigateway:<REGION>:states:action/StartSyncExecution",
    "httpMethod": "POST",
    "type": "aws",
    "credentials": "<APIGATEWAY_ROLE_ARN>",
    "requestTemplates": {
      "application/json": {
        "statusCode": "200"
      }
    }
  }
}
```

The API Gateway role needs `states:StartSyncExecution` on the
state machine ARN.

## Step 4 - Define the ASL with Express-compatible patterns (moved from SKILL.md)

Write the ASL definition. For fan-out, use Inline Map (≤40
concurrent) or Distributed Map (≤10,000 concurrent with S3 /
DynamoDB ItemReader). For job-style integrations, use `.sync`.

```json
{
  "StartAt": "FanOut",
  "States": {
    "FanOut": {
      "Type": "Map",
      "ItemProcessor": {
        "ProcessorConfig": { "Mode": "DISTRIBUTED" },
        "StartAt": "ProcessItem",
        "States": {
          "ProcessItem": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:process-item",
            "End": true
          }
        }
      },
      "ItemReader": {
        "Resource": "arn:aws:states:::s3:getObject",
        "Parameters": { "Bucket": "my-bucket", "Key": "input.json" }
      },
      "MaxConcurrency": 1000,
      "End": true
    }
  }
}
```

**Common mistake:** Inline Map on Express with > 40 concurrent
iterations. Inline Map caps at 40 concurrent; the rest queue. For
large fan-out on Express, use Distributed Map — but verify the
total iteration time still fits in the 5-minute cap.
