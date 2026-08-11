# End-to-End Example: DynamoDB Auto-Scaling Deployment

A walkthrough showing how to use the `dynamodb-autoscaling-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning DynamoDB auto-scaling for a PROVISIONED-mode
table with one GSI. The deployment needs:

- Table: orders-table (us-east-1, account 111111111111)
- Capacity mode: PROVISIONED (required for auto-scaling)
- Table RCU/WCU: Min=10, Max=40000, Target=70%, Cooldowns=60s
- GSI status-index RCU/WCU: Min=5, Max=20000, Target=70%, Cooldowns=60s
- Throttle alarm: ThrottledRequests > 0 → SNS alerts

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-dynamodb-autoscaling
```

Then paste the requirements.

### Option B: Natural language

```
You: "Configure DynamoDB auto-scaling for orders-table in PROVISIONED
      mode. Target 70% for table and GSI status-index. Min 10, Max
      40000 for table; Min 5, Max 20000 for GSI. Throttle alarm to
      my SNS alerts topic. Account: 111111111111."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "configure dynamodb autoscaling"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
DYNAMODB_AUTOSCALING: orders-table (arn:aws:dynamodb:us-east-1:111111111111:table/orders-table)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Table: orders-table (arn:aws:dynamodb:us-east-1:111111111111:table/orders-table)
  [✓] Capacity mode: PROVISIONED (required for auto-scaling)
  [✓] Application auto-scaling role: AWSServiceRoleForApplicationAutoScaling_DynamoDBFeedback (SLR)
  [✓] Table read scaling: scalable target (Min=10, Max=40000) + policy (Target=70%, ScaleOut=60s, ScaleIn=60s)
  [✓] Table write scaling: scalable target (Min=10, Max=40000) + policy (Target=70%, ScaleOut=60s, ScaleIn=60s)
  [✓] GSI status-index read scaling: scalable target (Min=5, Max=20000) + policy (Target=70%, ScaleOut=60s, ScaleIn=60s)
  [✓] GSI status-index write scaling: scalable target (Min=5, Max=20000) + policy (Target=70%, ScaleOut=60s, ScaleIn=60s)
  [✓] Throttle alarm: CloudWatch alarm on ThrottledRequests > 0 → arn:aws:sns:us-east-1:111111111111:alerts
  [✓] Tags: Owner=platform, Service=orders
VERIFICATION_COMMANDS:
  aws application-autoscaling describe-scalable-targets --service-namespace dynamodb --resource-ids table/orders-table
  aws application-autoscaling describe-scaling-policies --service-namespace dynamodb --resource-id table/orders-table
  aws dynamodb describe-table --table-name orders-table --query Table.BillingModeSummary
  aws cloudwatch describe-alarms --namespace AWS/DynamoDB --dimensions Name=TableName,Value=orders-table
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Verify prerequisites
aws dynamodb describe-table --table-name orders-table --query 'Table.[TableArn,BillingModeSummary.BillingMode]'
aws iam get-role --role-name AWSServiceRoleForApplicationAutoScaling_DynamoDBFeedback

# Step 2: Register scalable targets (table RCU + WCU)
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/orders-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity 10 --max-capacity 40000

aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/orders-table \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --min-capacity 10 --max-capacity 40000

# Step 3: Create target tracking policies (table RCU + WCU)
aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/orders-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-name orders-table-read-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":60}'

aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/orders-table \
  --scalable-dimension dynamodb:table:WriteCapacityUnits \
  --policy-name orders-table-write-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBWriteCapacityUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":60}'

# Step 4: Register GSI scalable targets + policies (status-index)
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id table/orders-table/index/status-index \
  --scalable-dimension dynamodb:index:ReadCapacityUnits \
  --min-capacity 5 --max-capacity 20000

aws application-autoscaling put-scaling-policy \
  --service-namespace dynamodb \
  --resource-id table/orders-table/index/status-index \
  --scalable-dimension dynamodb:index:ReadCapacityUnits \
  --policy-name status-index-read-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":60}'

# Step 5: Throttle alarm
aws cloudwatch put-metric-alarm \
  --alarm-name dynamodb-throttle-orders-table \
  --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=orders-table \
  --statistic Sum --period 300 \
  --threshold 1 --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:alerts
```

---

## Step 4 — Post-deployment verification

```bash
# Scalable targets registered
aws application-autoscaling describe-scalable-targets \
  --service-namespace dynamodb \
  --resource-ids table/orders-table

# Scaling policies attached
aws application-autoscaling describe-scaling-policies \
  --service-namespace dynamodb \
  --resource-id table/orders-table

# GSI scaling policies
aws application-autoscaling describe-scaling-policies \
  --service-namespace dynamodb \
  --resource-id table/orders-table/index/status-index

# Table still in PROVISIONED mode
aws dynamodb describe-table \
  --table-name orders-table \
  --query Table.BillingModeSummary
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Capacity mode | Ignores billing mode | Verifies PROVISIONED | Auto-scaling fails on on-demand tables |
| GSI auto-scaling | Configures table only | Configures table + every GSI | GSIs throttle independently |
| Target metric | Uses ConsumedRCU | Uses DynamoDBReadCapacityUtilization | Managed metric; ConsumedRCU is raw |
| Target utilization | Accepts default 50% | Recommends 70% for steady-state | 50% over-provisions by 2x |
| Cooldown tuning | Omits cooldowns | ScaleOut=60, ScaleIn=60 | Controls flapping and responsiveness |
| SLR role | Not checked | Verifies AWSServiceRoleForApplicationAutoScaling_DynamoDBFeedback | Missing SLR → AccessDenied |
| Throttle monitoring | Not configured | CloudWatch alarm on ThrottledRequests | Detects under-provisioning early |

---

## Related artifacts

- **Skill definition:** `skills/dynamodb-autoscaling-deployer/SKILL.md`
- **Target tracking guide:** `skills/dynamodb-autoscaling-deployer/references/target-tracking-and-cooldowns.md`
- **Capacity modes and throttling:** `skills/dynamodb-autoscaling-deployer/references/capacity-modes-and-throttling.md`
- **Slash command:** `commands/aws/deploy-dynamodb-autoscaling.md`
- **Eval suite:** `skills/dynamodb-autoscaling-deployer/evals/evals.json`
- **Legacy test cases:** `skills/dynamodb-autoscaling-deployer/eval/test-cases.yaml`
