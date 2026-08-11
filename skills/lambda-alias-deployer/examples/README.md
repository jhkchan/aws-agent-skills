# End-to-End Example: Lambda Alias Deployment

A walkthrough showing how to use the `lambda-alias-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production Lambda alias with canary traffic
shifting, provisioned concurrency, and API Gateway integration.
The alias needs:

- Function: my-function (exists in us-east-1)
- Current version: 5 (published, immutable)
- New version: 6 (published, canary candidate)
- Alias: prod (traffic shifting 90% v5, 10% v6)
- API Gateway: abc123 stage prod → alias prod
- Provisioned concurrency: 10 on alias prod
- CloudWatch alarm: errors scoped to my-function:prod

Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-lambda-alias
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a prod alias for my-function with canary traffic
      shifting: 90% on version 5, 10% on version 6. Set up
      provisioned concurrency at 10 on the alias. API Gateway
      abc123 stage prod. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a lambda alias"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
LAMBDA_ALIAS: my-function:prod (version 5, weight 90%; version 6, weight 10%)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Function: my-function (exists in us-east-1)
  [✓] Published version: 5 (current), 6 (canary)
  [✓] Alias: prod → version 5 (90%) + version 6 (10%)
  [✓] Traffic shifting: canary (version 5 90% → version 6 10%)
  [✓] API Gateway integration: abc123 stage prod → alias prod
  [✓] CloudWatch alarm: my-function-prod-errors scoped to my-function:prod
  [✓] Provisioned concurrency: 10 executions on alias prod
  [✓] SnapStart: disabled
  [✓] Tags: Environment=production, Service=api
VERIFICATION_COMMANDS:
  aws lambda get-alias --function-name my-function --name prod
  aws lambda get-provisioned-concurrency-config --function-name my-function --qualifier prod
  aws cloudwatch describe-alarms --alarm-names my-function-prod-errors
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the alias (if not existing) pointing to version 5
aws lambda create-alias \
  --function-name my-function \
  --name prod \
  --function-version 5 \
  --description "Production alias"

# Step 2: Set canary traffic (10% to version 6)
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 5 \
  --routing-config AdditionalVersionWeights='{"6":0.1}'

# Step 3: Configure provisioned concurrency on the alias
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 10

# Step 4: Grant API Gateway permission to invoke the alias
aws lambda add-permission \
  --function-name "my-function:prod" \
  --statement-id apigateway-prod \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:123456789012:abc123/*/GET/hello"

# Step 5: Create CloudWatch alarm scoped to alias
aws cloudwatch put-metric-alarm \
  --alarm-name "my-function-prod-errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 60 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=my-function Name=Resource,Value=my-function:prod \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:alerts"

# Step 6: After canary validation — finalize 100%
aws lambda update-alias \
  --function-name my-function \
  --name prod \
  --function-version 6 \
  --routing-config '{}'
```

---

## Step 4 — Post-deployment verification

```bash
# Alias configuration (should show version 5, routing config with v6 weight)
aws lambda get-alias \
  --function-name my-function \
  --name prod

# Provisioned concurrency (should show 10, state READY)
aws lambda get-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod

# CloudWatch alarm (should be active)
aws cloudwatch describe-alarms \
  --alarm-names my-function-prod-errors
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Version target | $LATEST | Published version (immutable) | $LATEST changes on every update; defeats traffic shifting |
| Traffic shift | All-at-once (100%) | Canary (10% → 25% → 50% → 100%) | All-at-once has no rollback safety |
| Provisioned concurrency | On version number | On alias name | Version-level PC is lost when alias re-points |
| API Gateway integration | Function ARN (no qualifier) | Function ARN with alias qualifier | Without qualifier, API Gateway invokes $LATEST |
| CloudWatch alarm | FunctionName dimension only | FunctionName + Resource dimension | Without Resource, alarm aggregates all versions |
| SnapStart | Enabled after publish | Enabled before publish | Snapshots are created at publish time |

---

## Related artifacts

- **Skill definition:** `skills/lambda-alias-deployer/SKILL.md`
- **Traffic shifting and concurrency:** `skills/lambda-alias-deployer/references/traffic-shifting-and-concurrency.md`
- **Provisioning CLI commands:** `skills/lambda-alias-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-lambda-alias.md`
- **Eval suite:** `skills/lambda-alias-deployer/evals/evals.json`
- **Legacy test cases:** `skills/lambda-alias-deployer/eval/test-cases.yaml`
