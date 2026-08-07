# End-to-End Example: Lambda Function Deployment

A walkthrough showing how to use the `lambda-function-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are deploying a production Lambda function that processes orders from
an SQS queue, writes to DynamoDB, and needs VPC access to reach an RDS
instance. The function requires:

- Least-privilege execution role (DynamoDB + SQS + RDS)
- Python 3.12 runtime
- 512 MB memory, 15s timeout
- VPC attachment (private subnets + NAT Gateway for AWS SDK calls)
- KMS-encrypted environment variables
- On-failure SQS destination
- X-Ray tracing
- CloudWatch log group with 30-day retention
- Powertools for Python layer

Function name: `order-processor-prod`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-lambda-function
```

Then paste the function requirements.

### Option B: Natural language

```
You: "Deploy a production Lambda function named order-processor-prod
      in us-east-1. Runtime python3.12, handler app.handler. Memory 512,
      timeout 15s. VPC subnets subnet-aaa, subnet-bbb with sg-orders.
      Needs DynamoDB orders-table + SQS orders-queue access. KMS key
      alias/lambda-env-key for env vars. On-failure destination
      order-dlq. X-Ray active. 30-day log retention. Powertools layer.
      Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy a lambda function"
```

Output:

```
[Phase: Deploy | Skills routed: lambda-function-deployer]

Primary route: lambda-function-deployer (score: 18)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
FUNCTION: order-processor-prod
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Execution IAM role — order-processor-exec (DynamoDB + SQS scoped)
  [✓]      Runtime — python3.12 (supported, not deprecated)
  [✓]      Memory — 512 MB
  [✓]      Timeout — 15s
  [✓]      Environment variables — KMS-encrypted (alias/lambda-env-key)
  [✓]      VPC — Private subnets (subnet-aaa, subnet-bbb) + sg-orders + NAT Gateway
  [✓]      Destination — On-failure SQS (order-dlq)
  [OPTIONAL] Concurrency — On-demand (no provisioned needed for SQS-triggered)
  [✓]      Layers — Powertools for Python v3 (python3.12-x86_64)
  [OPTIONAL] Code signing — Not configured
  [✓]      Packaging — Zip (8 MB compressed)
  [✓]      Logging — /aws/lambda/order-processor-prod, retention 30 days
  [✓]      Tracing — X-Ray Active mode
VERIFICATION_COMMANDS:
  aws lambda get-function-configuration --function-name order-processor-prod
  aws iam list-attached-role-policies --role-name order-processor-exec
  aws lambda get-function-event-invoke-config --function-name order-processor-prod
  aws logs describe-log-groups --log-group-name-prefix /aws/lambda/order-processor-prod
  aws lambda invoke --function-name order-processor-prod --payload '{"test": true}' /tmp/response.json
```

---

## Step 3 — Deployment commands

The skill generates the CLI sequence (from
`references/deployment-cli-commands.md`):

```bash
# Step 1: Create execution role with trust policy
aws iam create-role \
  --role-name order-processor-exec \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Scoped CloudWatch Logs (pre-create log group, no CreateLogGroup needed)
aws logs create-log-group --log-group-name /aws/lambda/order-processor-prod
aws logs put-retention-policy \
  --log-group-name /aws/lambda/order-processor-prod \
  --retention-in-days 30

aws iam put-role-policy \
  --role-name order-processor-exec \
  --policy-name order-processor-logs \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/order-processor-prod:*"
    }]
  }'

# Service-specific permissions (DynamoDB + SQS)
aws iam put-role-policy \
  --role-name order-processor-exec \
  --policy-name order-processor-service \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query"],
        "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/orders-table"
      },
      {
        "Effect": "Allow",
        "Action": ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage"],
        "Resource": "arn:aws:sqs:us-east-1:123456789012:orders-queue"
      }
    ]
  }'

# X-Ray tracing
aws iam attach-role-policy \
  --role-name order-processor-exec \
  --policy-arn arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess

# KMS decrypt for env var encryption
aws iam put-role-policy \
  --role-name order-processor-exec \
  --policy-name order-processor-kms \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["kms:Decrypt"],
      "Resource": "arn:aws:kms:us-east-1:123456789012:alias/lambda-env-key"
    }]
  }'

# Step 2: Create the function
aws lambda create-function \
  --function-name order-processor-prod \
  --runtime python3.12 \
  --handler app.handler \
  --role arn:aws:iam::123456789012:role/order-processor-exec \
  --zip-file fileb://function.zip \
  --memory-size 512 \
  --timeout 15 \
  --environment "Variables={ORDERS_TABLE=orders-table,QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/orders-queue}" \
  --kms-key-arn "arn:aws:kms:us-east-1:123456789012:alias/lambda-env-key" \
  --tracing-config Mode=Active \
  --vpc-config SubnetIds=subnet-aaa,subnet-bbb,SecurityGroupIds=sg-orders \
  --layers "arn:aws:lambda:us-east-1:017000801446:layer:AWSLambdaPowertoolsPythonV3-python312-x86_64:1"

# Step 3: On-failure destination
aws lambda put-function-event-invoke-config \
  --function-name order-processor-prod \
  --maximum-retry-attempts 2 \
  --maximum-event-age-in-seconds 21600 \
  --destination-config '{"OnFailure":{"Destination":"arn:aws:sqs:us-east-1:123456789012:order-dlq"}}'

# Step 4: Tags
aws lambda tag-resource \
  --resource arn:aws:lambda:us-east-1:123456789012:function:order-processor-prod \
  --tags Environment=production,Workload=order-processing
```

---

## Step 4 — Post-deployment verification

```bash
# Function configuration (runtime, memory, timeout, VPC, layers)
aws lambda get-function-configuration --function-name order-processor-prod

# Execution role policies
aws iam list-attached-role-policies --role-name order-processor-exec
aws iam list-inline-role-policies --role-name order-processor-exec

# Event invoke config (destination + retry config)
aws lambda get-function-event-invoke-config --function-name order-processor-prod

# Log group retention
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/order-processor-prod

# Test invocation
aws lambda invoke \
  --function-name order-processor-prod \
  --cli-binary-format raw-in-base64-out \
  --payload '{"test": true}' \
  /tmp/response.json
cat /tmp/response.json
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| CloudWatch log retention | Not set (unlimited) | 30 days | Lambda creates the log group automatically but does NOT set retention. Without it, logs accumulate indefinitely, incurring unbounded cost. |
| KMS decrypt on execution role | Not added | Added | When env vars use a customer-managed KMS key, the execution role needs `kms:Decrypt`. Without it, the function fails at cold start with `KMSAccessDeniedException`. |
| Scoped log permissions | `AWSLambdaBasicExecutionRole` (all log groups) | Scoped to `/aws/lambda/order-processor-prod` | The managed policy grants `logs:CreateLogGroup` on ALL log groups in ALL regions. Scoping to the function's log group is least-privilege. |
| On-failure destination | Not configured | SQS destination configured | Async invocations that fail after retries are silently discarded without a destination. This causes data loss for event-driven pipelines. |
| VPC + NAT Gateway | VPC attached, no NAT | NAT Gateway verified | VPC-attached functions cannot reach the internet or AWS public endpoints without a NAT Gateway. AWS SDK calls (SQS, DynamoDB) would timeout. |
| Layer version pinning | `:LATEST` or unspecified | Pinned to `:1` | Unversioned layer ARNs resolve to `$LATEST`, which can break the function when a new version is published. |

---

## Related artifacts

- **Skill definition:** `skills/lambda-function-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/lambda-function-deployer/references/deployment-cli-commands.md`
- **Runtime and VPC guide:** `skills/lambda-function-deployer/references/runtime-and-vpc-guide.md`
- **Slash command:** `commands/aws/deploy-lambda-function.md`
- **Eval suite:** `skills/lambda-function-deployer/evals/evals.json`
- **Legacy test cases:** `skills/lambda-function-deployer/eval/test-cases.yaml`
