# End-to-End Example: Lambda Function URL Deployment

A walkthrough showing how to use the `lambda-function-url-deployer`
skill from invocation through verification. Mirrors the
structured-eval pattern of shipping a concrete worked example per
skill.

---

## Scenario

You are provisioning a Lambda Function URL for an API handler with
AWS_IAM auth, BUFFERED invoke mode, full CORS configuration, and a
resource-based policy for the calling user. The deployment needs:

- Function: my-api-handler (runtime nodejs20.x)
- Auth: AWS_IAM
- Invoke mode: BUFFERED
- CORS: AllowOrigins https://app.example.com, methods GET and POST,
  headers content-type and authorization, expose x-request-id, max
  age 86400
- Timeout: 10 seconds (within the 15s function URL cap)
- Caller: arn:aws:iam::111122223333:user/alice
- Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-lambda-function-url
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Lambda function URL for my-api-handler with
      IAM auth, BUFFERED mode, CORS for app.example.com."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a lambda function url"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
LAMBDA_FUNCTION_URL: https://abc123def456.lambda-url.us-east-1.on.aws/
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Lambda function: my-api-handler (exists, runtime: nodejs20.x)
  [✓] Auth mode: AWS_IAM
  [✓] Invoke mode: BUFFERED
  [✓] CORS: AllowOrigins=["https://app.example.com"], AllowMethods=["GET","POST"], AllowHeaders=["content-type","authorization"], ExposeHeaders=["x-request-id"], MaxAgeSeconds=86400
  [✓] Timeout check: function timeout 10s (within 15s function URL cap)
  [✓] Dual-stack: IPv4 + IPv6 (automatic)
  [✓] Qualifier: $LATEST
  [✓] Resource-based policy: statement function-url-invoke grants lambda:InvokeFunctionUrl to arn:aws:iam::111122223333:user/alice
  [✓] CloudWatch metrics: UrlRequests, Url4xx, Url5xx, UrlLatency (automatic)
  [✓] Tags: Environment=production, Service=api
VERIFICATION_COMMANDS:
  aws lambda get-function-url-config --function-name my-api-handler --region us-east-1
  aws lambda get-policy --function-name my-api-handler --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the function URL with IAM auth, BUFFERED mode, and CORS
aws lambda create-function-url-config \
  --function-name my-api-handler \
  --auth-type AWS_IAM \
  --invoke-mode BUFFERED \
  --cors '{
    "AllowOrigins": ["https://app.example.com"],
    "AllowMethods": ["GET", "POST"],
    "AllowHeaders": ["content-type", "authorization"],
    "ExposeHeaders": ["x-request-id"],
    "MaxAgeSeconds": 86400
  }' \
  --region us-east-1

# Step 2: Add resource-based policy for the calling user
aws lambda add-permission \
  --function-name my-api-handler \
  --statement-id function-url-invoke \
  --action lambda:InvokeFunctionUrl \
  --principal arn:aws:iam::111122223333:user/alice \
  --function-url-auth-type AWS_IAM \
  --region us-east-1

# Step 3: Set up CloudWatch alarm for 5xx errors
aws cloudwatch put-metric-alarm \
  --alarm-name "lambda-url-5xx-my-api-handler" \
  --metric-name Url5xx \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=my-api-handler \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --period 300 \
  --evaluation-periods 1 \
  --statistic Sum \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Verify function URL config
aws lambda get-function-url-config \
  --function-name my-api-handler \
  --region us-east-1

# Verify resource-based policy
aws lambda get-policy \
  --function-name my-api-handler \
  --region us-east-1

# Check CloudWatch metrics (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name UrlRequests \
  --dimensions Name=FunctionName,Value=my-api-handler \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1

# Test the function URL (with SigV4 signing)
# Use the AWS SDK or aws-requests-auth for proper IAM signing
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| CORS | Handler-level only | Function URL --cors parameter | Preflight fails without URL-level CORS |
| Auth | Uses NONE for simplicity | AWS_IAM with resource-based policy | NONE auth is public internet |
| Timeout | Assumes function timeout applies | Warns about 15s function URL cap | Function URL invocations cap at 15s |
| Invoke mode | Picks BUFFERED blindly | Evaluates RESPONSE_STREAM use case | Streaming reduces first-byte latency |
| Resource-based policy | Not configured | add-permission with function-url-auth-type | IAM auth requires explicit policy grant |
| CloudWatch alarms | Not set up | put-metric-alarm for Url5xx | 5xx errors go unnoticed without alarms |
| Alias qualifier | Assumes URL follows alias | Explicit --qualifier update | URL stays on $LATEST without update |

---

## Related artifacts

- **Skill definition:** `skills/lambda-function-url-deployer/SKILL.md`
- **CORS and auth guide:** `skills/lambda-function-url-deployer/references/cors-and-auth.md`
- **Streaming and CloudFront guide:** `skills/lambda-function-url-deployer/references/streaming-and-cloudfront.md`
- **Slash command:** `commands/aws/deploy-lambda-function-url.md`
- **Eval suite:** `skills/lambda-function-url-deployer/evals/evals.json`
- **Legacy test cases:** `skills/lambda-function-url-deployer/eval/test-cases.yaml`
