# End-to-End Example: EventBridge Scheduler Deployment

A walkthrough showing how to use the `eventbridge-scheduler-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an EventBridge Scheduler schedule that invokes a
Lambda function every hour with exact-time precision, a retry policy,
and a dead-letter queue. The schedule needs:

- Schedule name: hourly-report
- Expression: rate(1 hour)
- Flexible time window: OFF (exact-time invocation)
- Target: Lambda function report-generator
- IAM role: Scheduler invocation role (auto-scoped)
- Target input: {"report_type": "hourly", "env": "prod"}
- Schedule group: prod-schedules
- Retry policy: max 3 attempts, max event age 3600s
- DLQ: arn:aws:sqs:us-east-1:123456789012:scheduler-dlq
- Tags: Environment=production, Team=data

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-eventbridge-scheduler
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an EventBridge Scheduler schedule called hourly-report
      that invokes Lambda report-generator every hour. Use OFF
      flexible time window. Add retry policy and DLQ."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an eventbridge schedule"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
SCHEDULER: hourly-report (rate(1 hour))
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Schedule name: hourly-report
  [✓] Schedule type: rate
  [✓] Expression: rate(1 hour) (timezone: UTC)
  [✓] Flexible time window: OFF (exact-time invocation)
  [✓] Target: Lambda — arn:aws:lambda:us-east-1:123456789012:function:report-generator
  [✓] IAM role: Scheduler-managed (auto-scoped to target ARN)
  [✓] Target input: {"report_type": "hourly", "env": "prod"}
  [✓] Schedule group: prod-schedules
  [✓] Retry policy: max 3 attempts, max age 3600s
  [✓] Dead-letter queue: arn:aws:sqs:us-east-1:123456789012:scheduler-dlq
  [✓] State: ENABLED
  [✓] CloudWatch metrics: Invocations, InvocationsFailed
  [✓] Tags: Environment=production, Team=data
VERIFICATION_COMMANDS:
  aws scheduler get-schedule --name hourly-report --group-name prod-schedules --region us-east-1
  aws scheduler list-schedules --group-name prod-schedules --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the schedule group
aws scheduler create-schedule-group \
  --name prod-schedules \
  --region us-east-1

# Step 2: Create the DLQ (must exist before schedule)
aws sqs create-queue \
  --queue-name scheduler-dlq \
  --attributes VisibilityTimeout=300,MessageRetentionPeriod=1209600 \
  --region us-east-1

DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/123456789012/scheduler-dlq \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text \
  --region us-east-1)

# Step 3: Create the Scheduler invocation IAM role
cat > /tmp/scheduler-trust.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "scheduler.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

ROLE_ARN=$(aws iam create-role \
  --role-name EventBridgeSchedulerInvokeRole \
  --assume-role-policy-document file:///tmp/scheduler-trust.json \
  --query 'Role.Arn' --output text \
  --region us-east-1)

# Step 4: Attach scoped permissions policy
cat > /tmp/scheduler-permissions.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:report-generator"
    },
    {
      "Effect": "Allow",
      "Action": "sqs:SendMessage",
      "Resource": "$DLQ_ARN"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name EventBridgeSchedulerInvokeRole \
  --policy-name SchedulerInvokePolicy \
  --policy-document file:///tmp/scheduler-permissions.json

# Step 5: Create the schedule
aws scheduler create-schedule \
  --name hourly-report \
  --group-name prod-schedules \
  --schedule-expression "rate(1 hour)" \
  --schedule-expression-timezone "UTC" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target "{
    \"RoleArn\": \"$ROLE_ARN\",
    \"Arn\": \"arn:aws:lambda:us-east-1:123456789012:function:report-generator\",
    \"Input\": \"{\\\"report_type\\\": \\\"hourly\\\", \\\"env\\\": \\\"prod\\\"}\",
    \"RetryPolicy\": {
      \"MaximumRetryAttempts\": 3,
      \"MaximumEventAgeInSeconds\": 3600
    },
    \"DeadLetterConfig\": {
      \"Arn\": \"$DLQ_ARN\"
    }
  }" \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Verify the schedule exists and is ENABLED
aws scheduler get-schedule \
  --name hourly-report \
  --group-name prod-schedules \
  --region us-east-1

# List all schedules in the group
aws scheduler list-schedules \
  --group-name prod-schedules \
  --region us-east-1

# Bulk disable for maintenance
aws scheduler update-schedule-group \
  --name prod-schedules \
  --state DISABLED \
  --region us-east-1

# Bulk re-enable after maintenance
aws scheduler update-schedule-group \
  --name prod-schedules \
  --state ENABLED \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Flexible time window | Not configured (defaults weirdly) | OFF (exact-time) with trade-off explained | OFF = precise but costly; MAXIMUM = cheaper but imprecise |
| IAM role | Tries to pre-create without iam:PassRole | Scheduler-managed role with scoped permissions | Caller needs iam:PassRole; role is auto-scoped per target |
| DLQ | Not configured | SQS DLQ with retry policy before max retries exhausted | Failed invocations need DLQ for error recovery |
| Schedule group | Not used | Group for bulk enable/disable | Groups enable maintenance window and env promotion patterns |
| Target input | Not passed | Constant JSON input to target | Input passed verbatim to Lambda on every invocation |
| Retry policy | Not configured | Max 3 attempts, max age 3600s | Retries with exponential backoff; configurable max attempts |
| Timezone | UTC assumed | Timezone explicitly specified | Cron is timezone-sensitive; rate is timezone-independent |

---

## Related artifacts

- **Skill definition:** `skills/eventbridge-scheduler-deployer/SKILL.md`
- **Schedule expressions and flex window guide:** `skills/eventbridge-scheduler-deployer/references/schedule-expressions-and-flex-window.md`
- **Targets, IAM, and error handling guide:** `skills/eventbridge-scheduler-deployer/references/targets-iam-and-error-handling.md`
- **Slash command:** `commands/aws/deploy-eventbridge-scheduler.md`
- **Eval suite:** `skills/eventbridge-scheduler-deployer/evals/evals.json`
- **Legacy test cases:** `skills/eventbridge-scheduler-deployer/eval/test-cases.yaml`
