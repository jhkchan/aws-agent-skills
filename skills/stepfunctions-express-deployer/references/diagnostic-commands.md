# Step Functions Express Workflows Deployer - diagnostic and pre-flight commands (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Step 2 - validate ASL definition CLI

```bash
# Validate the ASL definition (does NOT check duration)
aws stepfunctions validate-state-machine-definition \
  --definition file://definition.json --type EXPRESS
```

## Step 3 - Express-compatibility grep CLI

```bash
# Reject if any match
grep -E ':waitForTaskToken' definition.json && echo "INCOMPATIBLE"
```

## Step 7 - sync vs async invocation CLI and timeout warning

```bash
aws stepfunctions start-sync-execution \
  --state-machine-arn arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME> \
  --input '{"amount": 100}'
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME> \
  --input '{"amount": 100}'
```

**Common mistake:** fronting an Express workflow with API Gateway
sync and not aligning timeouts. API Gateway times out at 29s;
Express sync can run to 5 min. Set the API Gateway integration
timeout to 29000 ms and alarm on p99 execution duration > 25s.

## Step 9 - verification CLI

```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME>
# Expected: type EXPRESS, loggingConfiguration.level=ALL, includeExecutionData=true
aws logs describe-log-groups --log-group-name-prefix /aws/states/<NAME>
# Expected: retentionInDays > 0
aws events describe-rule --name <RULE_NAME>  # if scheduled; State ENABLED
aws cloudwatch describe-alarms --alarm-names <NAME>-failed  # StateValue OK
```

