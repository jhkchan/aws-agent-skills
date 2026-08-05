# End-to-end usage scenario: stepfunctions-statemachine-auditor

A walkthrough showing the skill auditing a Standard workflow that has an
over-permissive execution role (OVERPERMISSIVE_ROLE) AND missing execution
logging (NO_LOGGING), demonstrating precedence aggregation, the
includeExecutionData trap, and the role-scoping remediation workflow.

## Input (user prompt)

> Review this Step Functions state machine before we promote it from
> staging to production. It orchestrates our order pipeline — Lambda for
> fraud check, DynamoDB for order persistence, SQS for downstream
> warehouse notifications.

```json
{
  "Type": "STANDARD",
  "LoggingConfiguration": {"level": "ALL", "includeExecutionData": false},
  "TracingConfiguration": {"enabled": true},
  "RoleArn": "arn:aws:iam::111111111111:role/sfn-order-pipeline-staging",
  "Definition": {
    "StartAt": "FraudCheck",
    "States": {
      "FraudCheck": {
        "Type": "Task",
        "Resource": "arn:aws:lambda:us-east-1:111111111111:function:fraud-check",
        "TimeoutSeconds": 30,
        "Retry": [{"ErrorEquals": ["Lambda.ServiceException"], "IntervalSeconds": 2, "MaxAttempts": 3, "BackoffRate": 2.0}],
        "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "FraudFail"}],
        "Next": "PersistOrder"
      },
      "PersistOrder": {
        "Type": "Task",
        "Resource": "arn:aws:dynamodb:us-east-1:111111111111:table/orders",
        "TimeoutSeconds": 10,
        "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "DdbFail"}],
        "Next": "NotifyWarehouse"
      },
      "NotifyWarehouse": {
        "Type": "Task",
        "Resource": "arn:aws:sqs:us-east-1:111111111111:warehouse-q",
        "TimeoutSeconds": 10,
        "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "SqsFail"}],
        "Next": "OrderComplete"
      },
      "FraudFail": {"Type": "Fail", "Error": "FraudCheckFailed"},
      "DdbFail": {"Type": "Fail", "Error": "PersistenceFailed"},
      "SqsFail": {"Type": "Fail", "Error": "NotificationFailed"},
      "OrderComplete": {"Type": "Succeed"}
    }
  }
}
```

Execution role identity policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["lambda:*", "dynamodb:*", "sqs:*"], "Resource": "*"}
  ]
}
```

## Skill output

```text
STATE_MACHINE: arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline-staging
TYPE: STANDARD
VERDICT: OVERPERMISSIVE_ROLE
REASON: Execution role grants lambda:*, dynamodb:*, and sqs:* on Resource "*"
(Step 3) — the state machine has fan-out access to every Lambda function,
DynamoDB table, and SQS queue in the account. Logging is also partially
configured: includeExecutionData is false, making CloudWatch Logs
forensically near-useless even though level is ALL.
FINDINGS:
  - [OVERPERMISSIVE_ROLE] lambda:* on Resource "*" (Step 3) — can invoke,
    modify, or delete any Lambda function in the account
  - [OVERPERMISSIVE_ROLE] dynamodb:* on Resource "*" (Step 3) — can read,
    write, or delete any DynamoDB table including ones unrelated to orders
  - [OVERPERMISSIVE_ROLE] sqs:* on Resource "*" (Step 3) — can send,
    receive, or purge any SQS queue
  - [NO_LOGGING] LoggingConfiguration.includeExecutionData: false (Step 1)
    — state transitions are logged but NOT input/output payloads; for a
    fraud-check pipeline this means post-incident investigators cannot
    reconstruct which orders were processed or what fraud scores were
    returned
  - [OK] TracingConfiguration.enabled: true on STANDARD workflow (Step 2)
  - [OK] All Task states have Catch + TimeoutSeconds; FraudCheck has Retry
    for transient Lambda errors (Step 4)
REMEDIATION:
  1. OVERPERMISSIVE_ROLE — Replace the wildcard policy with scoped grants:
     - lambda:InvokeFunction on arn:aws:lambda:us-east-1:111111111111:function:fraud-check
     - dynamodb:PutItem, dynamodb:GetItem, dynamodb:UpdateItem on
       arn:aws:dynamodb:us-east-1:111111111111:table/orders
     - sqs:SendMessage on arn:aws:sqs:us-east-1:111111111111:warehouse-q
  2. NO_LOGGING — Set includeExecutionData to true:
     aws stepfunctions update-state-machine \
       --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline-staging \
       --logging-configuration level=ALL,includeExecutionData=true
  3. Back up the current definition before changes:
     aws stepfunctions describe-state-machine \
       --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline-staging \
       --output json > /tmp/order-pipeline-backup.json
```

## What the skill caught that a generic assistant misses

1. **The `includeExecutionData: false` trap.** A generic assistant sees
   `level: ALL` and says "logging is configured." The skill recognises
   that without `includeExecutionData: true`, CloudWatch Logs has state
   transitions but NOT the actual order payloads or fraud scores — for a
   fraud pipeline, this is the difference between "we can investigate"
   and "we know Step2 ran but not what it processed."

2. **The fan-out blast radius.** A generic assistant says "the role is
   broad." The skill decomposes the wildcard into the three services
   (Lambda, DynamoDB, SQS) and explains that one state machine compromise
   = read/write access to every Lambda, every table, every queue in the
   account — not just "broad access."

3. **Precedence-driven aggregation.** The verdict is OVERPERMISSIVE_ROLE
   (security first), with the logging gap noted as a secondary finding.
   The skill does not average or "summarise" — it picks the worst by
   precedence and enumerates every finding so the operator can remediate
   independently.

4. **Specific CLI remediation, not generic advice.** The skill emits the
   exact `update-state-machine` command with the correct
   `--logging-configuration` syntax, and a per-service list of the
   minimum actions needed on the specific ARNs.

## Slash-command invocation

```
/aws:audit-stepfunctions-statemachine
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this state machine before we promote it to production"
```

The orchestrator emits
`[Phase: Audit | Skills routed: stepfunctions-statemachine-auditor]` and
hands off to this skill for the VERDICT.

## Live-account follow-up (optional, requires AWS CLI)

After remediating the role and logging configuration, validate:

```bash
# Verify the role policy was scoped down
aws iam get-role-policy --role-name sfn-order-pipeline-staging \
  --policy-name Scoped --profile default --output json | jq '.PolicyDocument'

# Confirm logging now includes execution data
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline-staging \
  --profile default --output json | jq '.loggingConfiguration'

# Trigger a test execution and verify CloudWatch Logs has the payload
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline-staging \
  --input '{"orderId":"test-123","amount":42.50}' --profile default
```

Then monitor CloudWatch Logs for the log group to confirm both state
transitions AND input/output payloads are arriving.
