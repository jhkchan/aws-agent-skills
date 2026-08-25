# Step Functions State Machine Deployer - IAM and logging templates (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Step 8 - IAM execution role (least privilege)

The execution role is the identity under which EVERY service integration
runs. Its scope is the workflow's total blast radius.

**Trust policy (mandatory):**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "states.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

**Identity policy derivation (per-Task audit):**
Walk each `Task` state's `Resource` ARN and grant the corresponding named
action on the specific resource ARN. Example for a workflow invoking two
Lambdas and one DynamoDB table:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeLambdas",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": [
        "arn:aws:lambda:us-east-1:111111111111:function:ChargeOrderFn",
        "arn:aws:lambda:us-east-1:111111111111:function:NotifyCompleteFn"
      ]
    },
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"],
      "Resource": "arn:aws:dynamodb:us-east-1:111111111111:table/OrdersTable"
    }
  ]
}
```

**Special permissions by integration pattern:**
- `.sync` on ECS: needs `ecs:RunTask`, `ecs:DescribeTasks`, `ecs:StopTask`,
  and `iam:PassRole` (for the ECS task role).
- `.waitForTaskToken`: needs `states:SendTaskSuccess`,
  `states:SendTaskFailure`, `states:SendTaskHeartbeat` — usually granted
  to the external worker, not the execution role.
- Distributed Map reading from S3: needs `s3:GetObject` on the source
  bucket/key.
- Bedrock: needs `bedrock:InvokeModel` on the model ARN.
- Standard with X-Ray: needs `xray:PutTraceSegments` +
  `xray:PutTelemetryRecords`.
- Logging to CloudWatch: needs `logs:CreateLogDelivery`,
  `logs:PutLogEvents`, `logs:DescribeLogGroups`, `logs:GetLogDelivery`,
  `logs:UpdateLogDelivery`.

**NEVER use `Action: "*"` on the execution role.** This is
admin-equivalent — one compromised state machine = full account
compromise.

## Step 9 - Logging and tracing

**Express workflows (logging is MANDATORY):**
```json
"LoggingConfiguration": {
  "Level": "ALL",
  "IncludeExecutionData": true,
  "Destinations": [{
    "CloudWatchLogsLogGroup": { "LogGroupArn": "arn:aws:logs:us-east-1:111111111111:log-group:/aws/states/myworkflow:*" }
  }]
}
```
- `Level: ALL` + `IncludeExecutionData: true` is the only meaningful config.
- `Level: OFF`/`ERROR`/absent → no durable record (Express history expires
  in 5-60 min).
- The log group's ARN MUST end with `:*` (the trailing wildcard is
  required by Step Functions).
- The role MUST grant `logs:CreateLogDelivery`, `logs:PutLogEvents`,
  `logs:DescribeLogGroups`, `logs:GetLogDelivery`, `logs:UpdateLogDelivery`.

**Standard workflows (tracing is recommended):**
```json
"TracingConfiguration": { "Enabled": true }
```
- Honored only on Standard — silently no-op on Express.
- Role MUST grant `xray:PutTraceSegments` + `xray:PutTelemetryRecords`.
- Standard logging is optional (90-day history via API is a fallback) but
  recommended for CloudWatch alarms and metric filters.

