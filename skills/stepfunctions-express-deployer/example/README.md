# End-to-End Example: Step Functions Express Workflow Deployment

A walkthrough showing how to use the `stepfunctions-express-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are setting up a high-volume order-processing workflow that runs
asynchronously every 5 minutes via EventBridge. The workflow uses a
Distributed Map to fan out across items in an S3 object, calling a
Lambda per item. You need:

- Express Workflow (high volume, idempotent, < 5 min)
- Distributed Map with S3 ItemReader, MaxConcurrency 1000
- CloudWatch Logs at level ALL with includeExecutionData and 30-day retention
- Idempotent Lambda handler via IdempotencyKey from $$.Execution.Id
- IAM least-privilege execution role
- EventBridge schedule with target role
- CloudWatch alarm on ExecutionsFailed

Workflow name: `order-processor`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-stepfunctions-express
```

Then paste the workflow requirements.

### Option B: Natural language

```
You: "Provision an Express workflow order-processor in us-east-1,
      account 123456789012. Distributed Map reading from
      my-bucket/input.json, Lambda process-item per item,
      MaxConcurrency 1000. CloudWatch Logs ALL with
      includeExecutionData. IdempotencyKey from $$.Execution.Id.
      EventBridge rate(5 minutes) + alarm on ExecutionsFailed."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create express workflow"
```

Output:

```
[Phase: Deploy | Skills routed: stepfunctions-express-deployer]
Primary route: stepfunctions-express-deployer (score: 19)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
EXPRESS_WORKFLOW: order-processor
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Express-vs-Standard decision: EXPRESS (Distributed Map, high-volume, idempotent)
  [✓] Duration budget: per-item < 1s, MaxConcurrency 1000 fits in 5-min cap
  [✓] No .waitForTaskToken in ASL: verified (grep returned 0 matches)
  [✓] ASL definition validated: Distributed Map + Lambda Task + S3 ItemReader
  [✓] IAM execution role: scoped to lambda:InvokeFunction on process-item + s3:GetObject
  [✓] Logging: /aws/states/order-processor, level ALL, includeExecutionData=true, retention 30d
  [✓] Invocation mode: async (EventBridge rate(5 minutes))
  [✓] EventBridge schedule + CloudWatch alarm: rate(5 minutes) + alarm on ExecutionsFailed
  [✓] Idempotency: Lambda uses IdempotencyKey.$: $$.Execution.Id
VERIFICATION_COMMANDS:
  aws stepfunctions describe-state-machine --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:order-processor
  aws logs describe-log-groups --log-group-name-prefix /aws/states/order-processor
  aws events describe-rule --name order-processor-schedule
  aws cloudwatch describe-alarms --alarm-names order-processor-failed
```

---

## Step 3 — Provisioning commands

```bash
# Create the log group first (with retention)
aws logs create-log-group --log-group-name /aws/states/order-processor
aws logs put-retention-policy --log-group-name /aws/states/order-processor \
  --retention-in-days 30

# Create the IAM execution role
cat > trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "states.us-east-1.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role --role-name order-processor-role \
  --assume-role-policy-document file://trust-policy.json

# Attach least-privilege inline policy
aws iam put-role-policy --role-name order-processor-role \
  --policy-name order-processor-inline \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      { "Effect": "Allow", "Action": "lambda:InvokeFunction",
        "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-item" },
      { "Effect": "Allow", "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::my-bucket/input.json" },
      { "Effect": "Allow",
        "Action": ["logs:CreateLogDelivery","logs:GetLogDelivery","logs:UpdateLogDelivery",
                   "logs:DeleteLogDelivery","logs:ListLogDeliveries","logs:PutLogEvents"],
        "Resource": "*" }
    ]
  }'

# Create the Express state machine with logging
aws stepfunctions create-state-machine \
  --name order-processor \
  --definition file://definition.json \
  --role-arn arn:aws:iam::123456789012:role/order-processor-role \
  --type EXPRESS \
  --logging-configuration \
    level=ALL,includeExecutionData=true,\
    destinations='[{CloudWatchLogsLogGroup={LogGroupArn=arn:aws:logs:us-east-1:123456789012:log-group:/aws/states/order-processor:*}}]'

# Configure EventBridge rule + target
aws events put-rule --name order-processor-schedule \
  --schedule-expression "rate(5 minutes)"

aws events put-targets --rule order-processor-schedule \
  --targets 'Id=1,Arn=arn:aws:states:us-east-1:123456789012:stateMachine:order-processor,RoleArn=arn:aws:iam::123456789012:role/events-target-role'

# Alarm on ExecutionsFailed
aws cloudwatch put-metric-alarm \
  --alarm-name order-processor-failed \
  --metric-name ExecutionsFailed \
  --namespace AWS/States \
  --dimensions Name=StateMachineArn,Value=arn:aws:states:us-east-1:123456789012:stateMachine:order-processor \
  --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold \
  --period 60 --evaluation-periods 1 --treat-missing-data notBreaching
```

---

## Step 4 — Post-deployment verification

```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:order-processor
# Expected: type EXPRESS, loggingConfiguration.level=ALL, includeExecutionData=true

aws logs describe-log-groups --log-group-name-prefix /aws/states/order-processor
# Expected: retentionInDays=30

aws events describe-rule --name order-processor-schedule
# Expected: State ENABLED, ScheduleExpression="rate(5 minutes)"

aws cloudwatch describe-alarms --alarm-names order-processor-failed
# Expected: StateValue OK
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| CloudWatch Logs at ALL | Omitted | /aws/states/order-processor with level ALL | Async Express has no caller to surface errors. Without logging, the 5-min execution history rolls over and failures are invisible. |
| includeExecutionData | false | true | Without execution data, logs show only metadata; RCA is impossible. |
| IdempotencyKey source | "Lambda is idempotent" (no key) | `$$.Execution.Id` persisted in DynamoDB | Express is at-least-once; without a deterministic key persisted before the side effect, retries can double-execute. |
| EventBridge target role | Omitted | Configured with trust to events.amazonaws.com | Without the target role, the rule fires (Invocations: 1) but no execution starts (Executions: 0) — silent failure. |
| CloudWatch alarm on ExecutionsFailed | Skipped | Configured | Async Express has no caller to surface errors; without an alarm, the failure may go undetected for days. |
| Distributed Map duration check | Skipped | Verified per-item time × concurrency fits in 5-min cap | Express caps at 5 min; a Distributed Map exceeding the cap fails mid-iteration with no progress signal. |

---

## Related artifacts

- **Skill definition:** `skills/stepfunctions-express-deployer/SKILL.md`
- **ASL patterns:** `skills/stepfunctions-express-deployer/references/express-asl-patterns.md`
- **IAM and logging templates:** `skills/stepfunctions-express-deployer/references/iam-and-logging-templates.md`
- **Slash command:** `commands/aws/deploy-stepfunctions-express.md`
- **Eval suite:** `skills/stepfunctions-express-deployer/evals/evals.json`
- **Legacy test cases:** `skills/stepfunctions-express-deployer/eval/test-cases.yaml`
