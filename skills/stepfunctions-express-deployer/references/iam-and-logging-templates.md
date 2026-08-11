# IAM and Logging Templates — Step Functions Express Deployer

Reference IAM role, trust policy, and logging-configuration
templates for Express Workflows. Substitute `<REGION>`,
`<ACCOUNT>`, `<NAME>`, `<ROLE_NAME>`, `<FUNCTION_ARN>`,
`<BUCKET>`, `<TABLE>` as needed. Stored here so the main skill
body stays scannable; see the 9-step procedure for when to apply
each variant.

## 1. Execution role trust policy

The service principal is region-scoped: `states.<REGION>.amazonaws.com`.
A common migration bug is to use the global `states.amazonaws.com`
principal, which works in us-east-1 but fails in other regions
when cross-region is attempted.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "states.<REGION>.amazonaws.com" },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {
        "sts:Externalid": "<ACCOUNT>"
      }
    }
  }]
}
```

The `sts:Externalid` condition is optional but recommended for
cross-account scenarios.

## 2. Inline least-privilege policy

Scope each integration to its specific resource ARN. Avoid
`Resource: "*"` unless the integration explicitly requires it
(e.g., AWS SDK integrations that call account-level operations).

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeProcessItemLambda",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:process-item"
    },
    {
      "Sid": "ReadS3Input",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::<BUCKET>/input.json"
    },
    {
      "Sid": "DynamoDBIdempotency",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:<REGION>:<ACCOUNT>:table/<TABLE>"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogDelivery",
        "logs:GetLogDelivery",
        "logs:UpdateLogDelivery",
        "logs:DeleteLogDelivery",
        "logs:ListLogDeliveries",
        "logs:PutLogEvents",
        "logs:PutDestination",
        "logs:PutSubscriptionFilter"
      ],
      "Resource": "*"
    },
    {
      "Sid": "XRayTracing",
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetSamplingRules",
        "xray:GetSamplingTargets"
      ],
      "Resource": "*"
    }
  ]
}
```

The `logs:*` permissions must use `Resource: "*"` because CloudWatch
Logs delivers logs via an internal account-level delivery resource.

## 3. EventBridge target role

The role assumed BY EventBridge to start Express executions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "events.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

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

Without the target role, the EventBridge rule fires (Invocations:
1) but no execution starts (Executions: 0) — silent failure.

## 4. API Gateway role for sync invocation

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "states:StartSyncExecution",
    "Resource": "arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME>"
  }]
}
```

The trust policy MUST allow API Gateway to assume the role:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "apigateway.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

## 5. Logging configuration

The `loggingConfiguration` block is part of the state machine
definition, not a separate API call:

```json
{
  "loggingConfiguration": {
    "level": "ALL",
    "includeExecutionData": true,
    "destinations": [
      {
        "CloudWatchLogsLogGroup": {
          "LogGroupArn": "arn:aws:logs:<REGION>:<ACCOUNT>:log-group:/aws/states/<NAME>:*"
        }
      }
    ]
  }
}
```

Level semantics:
- `ALL`: log every execution change (Start, StateEntered, StateExited, End). Highest cost; full RCA.
- `ERROR`: log only execution failures and state errors. Medium cost.
- `FATAL`: log only workflow-level fatal errors. Lowest cost; near-useless.
- `OFF`: no logging. NEVER for async Express.

`includeExecutionData=true` records input/output at each transition.
For PII workflows, redact at the workflow input via `InputPath` or
`Parameters` rather than disabling execution data wholesale.

## 6. CloudWatch Logs log group with retention

```bash
aws logs create-log-group \
  --log-group-name /aws/states/<NAME>

aws logs put-retention-policy \
  --log-group-name /aws/states/<NAME> \
  --retention-in-days 30
```

Without retention, the log group grows indefinitely. 30 days is
the common default; 7 days for high-volume dev workflows; 90+ days
for regulated workloads.

## 7. X-Ray tracing configuration

```json
{
  "tracingConfiguration": {
    "enabled": true
  }
}
```

The execution role needs `xray:PutTraceSegments` and
`xray:PutTelemetryRecords` (see Section 2). Without tracing, you
cannot visualize cross-service latency for sync Express workflows
invoked from API Gateway.

## 8. Cross-account execution caller policy

For a caller in account B to start executions on a state machine in
account A, the caller's identity policy needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "states:StartExecution",
    "Resource": "arn:aws:states:<REGION>:<ACCOUNT_A>:stateMachine:<NAME>"
  }]
}
```

The `states:StateMachineArn` condition key can scope which state
machines the caller can target — useful for tenant-isolation
patterns in multi-tenant SaaS.
