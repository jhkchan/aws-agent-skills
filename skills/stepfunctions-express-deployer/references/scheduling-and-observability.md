# Step Functions Express Workflows Deployer - scheduling and observability (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Step 8 - EventBridge scheduling + observability

#### 8a. EventBridge rule for scheduled Express

```bash
# Schedule: every 5 minutes
aws events put-rule --name <RULE_NAME> \
  --schedule-expression "rate(5 minutes)"

# Target: the Express state machine
aws events put-targets --rule <RULE_NAME> \
  --targets 'Id=1,Arn=arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME>,RoleArn=arn:aws:iam::<ACCOUNT>:role/<EVENTBRIDGE_ROLE>'
```

The EventBridge target role MUST trust `events.amazonaws.com` and
allow `states:StartExecution` on the state machine ARN. Without
the target role, the rule fires but no execution starts —
EventBridge shows `Invocations: 1`, Step Functions shows
`Executions: 0`, with no error.

#### 8b. CloudWatch alarms

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "<NAME>-failed" \
  --metric-name "ExecutionsFailed" \
  --namespace "AWS/States" \
  --dimensions Name=StateMachineArn,Value=arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME> \
  --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold \
  --period 60 --evaluation-periods 1 --treat-missing-data notBreaching
```

Always alarm on `ExecutionsFailed` for async Express — there is no
caller to surface the error.

#### 8c. X-Ray tracing

```bash
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME> \
  --tracing-configuration enabled=true
```

X-Ray tracing requires the execution role to have
`xray:PutTraceSegments` and `xray:PutTelemetryRecords`.

