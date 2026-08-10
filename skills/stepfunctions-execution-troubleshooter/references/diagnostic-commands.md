# Step Functions diagnostic command reference

Canonical command script for the `stepfunctions-execution-troubleshooter`
skill. Run these in order; each command's output narrows the decision
tree.

## 1. Identify the failing execution

```bash
aws stepfunctions list-executions --state-machine-arn <sm-arn> \
  --status FAILED --max-results 5 \
  --query 'executions[*].{arn:executionArn,name:name,status:status,startDate:startDate,stopDate:stopDate}'
```

## 2. Read the execution status, error, and cause

```bash
aws stepfunctions describe-execution --execution-arn <arn> \
  --query '{status:status,error:error,cause:cause,stateMachineArn:stateMachineArn,redriveStatus:redriveStatus,startDate:startDate,stopDate:stopDate,input:input,output:output}'
```

The `error` is the States.* category. The `cause` is the downstream
SDK error or runtime detail. READ BOTH.

## 3. Read the execution history to find the failing state

```bash
aws stepfunctions get-execution-history --execution-arn <arn> \
  --query 'events[?type==`TaskFailed` || type==`ExecutionFailed` || type==`TaskTimedOut`].{type:type,stateName:stateEnteredEventDetails.name,error:taskFailedEventDetails.error,cause:taskFailedEventDetails.cause}' \
  --output json
```

For larger executions, page via `--next-token` or use:

```bash
aws stepfunctions get-execution-history --execution-arn <arn> \
  --include-execution-data \
  --query 'events[*].{type:type,timestamp:timestamp,stateName:stateEnteredEventDetails.name,id:id,previousEventId:previousEventId}'
```

For EXPRESS workflows, history is best-effort via CloudWatch Logs.
Query the vended log group:

```bash
aws logs filter-log-events \
  --log-group-name /aws/vendedlogs/states/express-<sm-name>-Logs-<hash> \
  --filter-pattern "ExecutionFailed" \
  --start-time <epoch-ms> \
  --limit 50
```

## 4. Read the state machine definition and workflow type

```bash
aws stepfunctions describe-state-machine --state-machine-arn <sm-arn> \
  --query '{type:type,roleArn:roleArn,definition:definitionString}'

# Parse the failing state's ASL:
aws stepfunctions describe-state-machine --state-machine-arn <sm-arn> \
  --query 'definitionString' --output text \
  | jq '.States["<state-name>"] | {Type,Resource,TimeoutSeconds,HeartbeatSeconds,Retry,Catch,Next,Parameters,InputPath,OutputPath,ResultPath,ItemsPath}'
```

## 5. Read CloudWatch Metrics for throttling and limits

```bash
aws cloudwatch get-metric-statistics --namespace AWS/States \
  --metric-name ExecutionsFailed --dimensions Name=StateMachineArn,Value=<sm-arn> \
  --start-time <iso> --end-time <iso> --period 300 --statistics Sum

aws cloudwatch get-metric-statistics --namespace AWS/States \
  --metric-name ExecutionThrottled --dimensions Name=StateMachineArn,Value=<sm-arn> \
  --start-time <iso> --end-time <iso> --period 300 --statistics Sum

aws cloudwatch get-metric-statistics --namespace AWS/States \
  --metric-name ThrottledStateTransition --dimensions Name=StateMachineArn,Value=<sm-arn> \
  --start-time <iso> --end-time <iso> --period 300 --statistics Sum
```

`ExecutionThrottled > 0` indicates account-level throttling.
`ThrottledStateTransition > 0` indicates transition-quota throttling.

## 6. For IAM / PERMISSION_DENIED: simulate the state machine role

```bash
aws stepfunctions describe-state-machine --state-machine-arn <sm-arn> \
  --query 'roleArn' --output text

aws iam simulate-principal-policy \
  --policy-source-arn <state-machine-role-arn> \
  --action-names <service>:<Action> \
  --resource-arns <resource-arn>
```

For cross-account, also read the target resource's policy:

```bash
# KMS key policy
aws kms get-key-policy --key-id <key-id> --policy-name default

# SQS queue policy
aws sqs get-queue-attributes --queue-url <url> --attribute-names Policy

# Lambda resource-based policy
aws lambda get-policy --function-name <name>

# Cross-account state machine
aws stepfunctions describe-state-machine --state-machine-arn <target-sm-arn>
```

## 7. For TASK_FAILED on Lambda: read the function logs

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --filter-pattern "ERROR" \
  --start-time <epoch-ms> \
  --limit 50 \
  --query 'events[*].{timestamp:timestamp,message:message}'
```

## 8. For TASK_TIMEOUT on activity tasks: verify heartbeats in CloudTrail

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=SendTaskHeartbeat \
  --start-time <iso> --end-time <iso> \
  --max-results 20
```

If `SendTaskHeartbeat` events are missing or sparse relative to
`HeartbeatSeconds`, the worker is not heartbeating.

## 9. For Distributed Map failures: read the Map Run

```bash
# Identify the Map Run ARN from the parent execution history:
aws stepfunctions get-execution-history --execution-arn <parent-arn> \
  --query 'events[?type==`MapRunStarted`].mapRunStartedEventDetails.mapRunArn'

# Describe the Map Run for iteration counts and failures:
aws stepflows describe-map-run --map-run-arn <map-run-arn> \
  --query '{status:status,executionCounts:executionCounts,itemCounts:itemCounts}'
```

(Distributed Map child execution ARNs are surfaced via the Map Run and
can be diagnosed individually with `describe-execution` /
`get-execution-history`.)

## 10. For redrive candidates: verify eligibility

```bash
aws stepfunctions describe-execution --execution-arn <arn> \
  --query '{status:status,redriveStatus:redriveStatus,stateMachineArn:stateMachineArn}'

# Verify workflow type is STANDARD (no :express: in the ARN):
aws stepfunctions describe-state-machine --state-machine-arn <sm-arn> \
  --query 'type' --output text
```

If `type` is `EXPRESS`, redrive is NOT supported — start a new
execution with the original input.

## 11. Verify the fix

```bash
# Test the state with the fixed ASL before deploying:
aws stepfunctions test-state \
  --definition <fixed-asl-for-state> \
  --role-arn <role-arn> \
  --input file://test-input.json \
  --query '{status:status,output:output,error:error}'

# Or run a full execution with a known input:
aws stepfunctions start-execution \
  --state-machine-arn <sm-arn> \
  --name verification-$(date +%s) \
  --input file://test-input.json
```

## 12. Redrive (Standard only)

```bash
aws stepfunctions redrive-execution --execution-arn <arn> \
  --query '{redriveDate:redriveDate,redriveStatus:redriveStatus}'
```

Confirm `redriveStatus` transitions to `REDRIVING` then re-poll
`describe-execution` until status is `SUCCEEDED` or `FAILED`.
