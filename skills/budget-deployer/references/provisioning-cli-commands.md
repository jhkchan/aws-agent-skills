# Provisioning CLI Commands — AWS Budget Deployer

Full copy-pasteable CLI command sequence for all 10 provisioning steps.
Variables to substitute: `<account-id>`, `<budget-name>`, `<topic-arn>`,
`<role-arn>`, `<region>`, `<policy-arn>`, threshold values.

## Step 0: Prerequisites check

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"

# Confirm SNS topic exists and policy allows budgets.amazonaws.com + ce.amazonaws.com
aws sns get-topic-attributes --topic-arn <topic-arn> \
  --query 'Attributes.Policy' --output text | grep -E 'budgets|ce\.amazonaws'

# Confirm the budget action role trusts budgets.amazonaws.com
aws iam get-role --role-name BudgetActionsRole \
  --query 'Role.AssumeRolePolicyDocument.Statement[].Principal.Service' --output text

# If the role does not exist, create it:
cat > /tmp/budget-trust.json <<'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"budgets.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF
aws iam create-role --role-name BudgetActionsRole \
  --assume-role-policy-document file:///tmp/budget-trust.json
```

## Step 1: Create a cost budget

```bash
aws budgets create-budget \
  --account-id <account-id> \
  --budget '{"BudgetName":"<budget-name>","BudgetLimit":{"Amount":"10000","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST","CostTypes":{"IncludeTax":true,"IncludeSubscription":true,"UseBlended":false,"IncludeRefund":false,"IncludeCredit":true,"IncludeUpfront":true,"IncludeRecurring":true,"IncludeOtherSubscription":true,"IncludeSupport":true,"IncludeDiscount":true,"UseAmortized":false}}'
```

### Zero-spend variant

```bash
aws budgets create-budget --account-id <account-id> \
  --budget '{"BudgetName":"zero-spend","BudgetLimit":{"Amount":"0.01","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}'
```

### With CostFilters (e.g., per service)

```bash
aws budgets create-budget --account-id <account-id> \
  --budget '{"BudgetName":"ec2-budget","BudgetLimit":{"Amount":"5000","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST","CostFilters":{"Service":["Amazon Elastic Compute Cloud - Compute"]}}'
```

## Step 2: Create a usage budget (RI/SP)

```bash
# RI Utilization
aws budgets create-budget --account-id <account-id> \
  --budget '{"BudgetName":"ri-util","BudgetLimit":{"Amount":"80","Unit":"PERCENTAGE"},"TimeUnit":"MONTHLY","BudgetType":"RI_UTILIZATION"}'

# RI Coverage
aws budgets create-budget --account-id <account-id> \
  --budget '{"BudgetName":"ri-cov","BudgetLimit":{"Amount":"80","Unit":"PERCENTAGE"},"TimeUnit":"MONTHLY","BudgetType":"RI_COVERAGE"}'

# Savings Plan Utilization (2024-2025 GA)
aws budgets create-budget --account-id <account-id> \
  --budget '{"BudgetName":"sp-util","BudgetLimit":{"Amount":"80","Unit":"PERCENTAGE"},"TimeUnit":"MONTHLY","BudgetType":"SP_UTILIZATION"}'

# Savings Plan Coverage
aws budgets create-budget --account-id <account-id> \
  --budget '{"BudgetName":"sp-cov","BudgetLimit":{"Amount":"80","Unit":"PERCENTAGE"},"TimeUnit":"MONTHLY","BudgetType":"SP_COVERAGE"}'
```

## Step 3: Attach notifications

```bash
# COST budget — 80/90/100% ACTUAL + 100% FORECAST (repeat per threshold)
for pct in 80 90 100; do
  aws budgets create-notification --account-id <account-id> \
    --budget-name <budget-name> \
    --notification "{\"NotificationType\":\"ACTUAL\",\"ComparisonOperator\":\"GREATER_THAN\",\"Threshold\":${pct},\"ThresholdType\":\"PERCENTAGE\"}" \
    --subscribers Address=<topic-arn>,Type=SNS
done

aws budgets create-notification --account-id <account-id> \
  --budget-name <budget-name> \
  --notification '{"NotificationType":"FORECAST","ComparisonOperator":"GREATER_THAN","Threshold":100,"ThresholdType":"PERCENTAGE"}' \
  --subscribers Address=<topic-arn>,Type=SNS

# USAGE budget (RI/SP) — LESS_THAN_THRESHOLD (alerts when below target)
aws budgets create-notification --account-id <account-id> \
  --budget-name <usage-budget-name> \
  --notification '{"NotificationType":"ACTUAL","ComparisonOperator":"LESS_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"}' \
  --subscribers Address=<topic-arn>,Type=SNS
```

## Step 4: Create budget actions

```bash
# APPLY_IAM_POLICY
aws budgets create-budget-action \
  --account-id <account-id> --budget-name <budget-name> \
  --notification-type ACTUAL --action-type APPLY_IAM_POLICY \
  --action-threshold '{"ActionThresholdValue":100,"ActionThresholdType":"PERCENTAGE"}' \
  --definition '{"IamActionDefinition":{"PolicyArn":"<policy-arn>","Roles":["<role-name>"]}}' \
  --execution-role-arn <execution-role-arn> \
  --approval-model AUTOMATIC

# RUN_SSM_DOCUMENTS — STOP_EC2_INSTANCES
aws budgets create-budget-action \
  --account-id <account-id> --budget-name <budget-name> \
  --notification-type ACTUAL --action-type RUN_SSM_DOCUMENTS \
  --action-threshold '{"ActionThresholdValue":100,"ActionThresholdType":"PERCENTAGE"}' \
  --definition '{"SsmActionDefinition":{"ActionSubType":"STOP_EC2_INSTANCES","Region":"<region>","InstanceIds":["<instance-id>"]}}' \
  --execution-role-arn <execution-role-arn> \
  --approval-model AUTOMATIC

# RUN_SSM_DOCUMENTS — STOP_RDS_INSTANCE (2024 GA)
aws budgets create-budget-action \
  --account-id <account-id> --budget-name <budget-name> \
  --notification-type ACTUAL --action-type RUN_SSM_DOCUMENTS \
  --action-threshold '{"ActionThresholdValue":100,"ActionThresholdType":"PERCENTAGE"}' \
  --definition '{"SsmActionDefinition":{"ActionSubType":"STOP_RDS_INSTANCE","Region":"<region>","InstanceIds":["<db-instance-id>"]}}' \
  --execution-role-arn <execution-role-arn> \
  --approval-model AUTOMATIC
```

## Step 5: Cost Anomaly Detection

```bash
# Dimensional SERVICE monitor (cleaner signals than default account-wide)
aws ce create-anomaly-monitor \
  --anomaly-monitor '{"Name":"service-anomaly-monitor","Type":"DIMENSIONAL","MonitorDimension":"SERVICE"}'

# Subscription (default monitor is arn:aws:ce::<acct>:anomaly-monitor/default)
aws ce create-anomaly-subscription \
  --anomaly-subscription '{"Name":"<subscription-name>","Frequency":"DAILY","Threshold":100.0,"MonitorArn":"arn:aws:ce::<account-id>:anomaly-monitor/default","Subscribers":[{"Address":"<topic-arn>","Type":"SNS"}]}'
```

## Step 6: SNS topic + policy (if creating new)

```bash
TOPIC_ARN=$(aws sns create-topic --name budget-alerts --region us-east-1 --query TopicArn --output text)

cat > /tmp/budget-topic-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": ["budgets.amazonaws.com", "ce.amazonaws.com"]},
    "Action": "sns:Publish",
    "Resource": "$TOPIC_ARN"
  }]
}
EOF
aws sns set-topic-attributes --topic-arn "$TOPIC_ARN" \
  --attribute-name Policy --attribute-value file:///tmp/budget-topic-policy.json

aws sns subscribe --topic-arn "$TOPIC_ARN" --protocol email \
  --notification-endpoint finops@example.com
```

## Verification

```bash
aws budgets describe-budget --account-id <account-id> --budget-name <budget-name>
aws budgets describe-notifications-for-budget --account-id <account-id> --budget-name <budget-name>
aws budgets describe-budget-actions --account-id <account-id> --budget-name <budget-name>
aws ce get-anomaly-monitors
aws ce get-anomaly-subscriptions
aws sns get-topic-attributes --topic-arn <topic-arn>
aws sns list-subscriptions-by-topic --topic-arn <topic-arn>
```

## Terraform equivalent (aws_budgets_budget)

```hcl
resource "aws_budgets_budget" "cost" {
  account_id = "<account-id>"
  name       = "prod-monthly-cost"
  budget_type = "COST"
  limit_amount = "10000"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name = "Service"
    values = ["Amazon Elastic Compute Cloud - Compute"]
  }
}

resource "aws_budgets_budget_action" "deny" {
  account_id          = "<account-id>"
  budget_name         = aws_budgets_budget.cost.name
  notification_type   = "ACTUAL"
  action_type         = "APPLY_IAM_POLICY"
  approval_model      = "AUTOMATIC"
  execution_role_arn  = aws_iam_role.budget_actions.arn

  action_threshold {
    action_threshold_value  = 100
    action_threshold_type   = "PERCENTAGE"
  }

  definition {
    iam_action_definition {
      policy_arn = aws_iam_policy.budget_deny_all.arn
      roles      = ["SandboxAppRole"]
    }
  }
}

resource "aws_iam_role" "budget_actions" {
  name = "BudgetActionsRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "budgets.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_ce_anomaly_subscription" "anomaly" {
  name      = "prod-anomaly-subscription"
  threshold = 100.0
  frequency = "DAILY"
  monitor_arn = "arn:aws:ce::<account-id>:anomaly-monitor/default"

  subscriber {
    type    = "SNS"
    address = aws_sns_topic.budget_alerts.arn
  }
}

resource "aws_sns_topic" "budget_alerts" {
  name = "budget-alerts"
}

resource "aws_sns_topic_policy" "budget_alerts" {
  arn = aws_sns_topic.budget_alerts.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = ["budgets.amazonaws.com", "ce.amazonaws.com"] }
      Action = "sns:Publish"
      Resource = aws_sns_topic.budget_alerts.arn
    }]
  })
}
```

## Step 3 — Cost budget configuration (CLI) (moved from SKILL.md)

```bash
aws budgets create-budget \
  --account-id 111111111111 \
  --budget '{"BudgetName":"prod-monthly-cost","BudgetLimit":{"Amount":"10000","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST","CostFilters":{"Service":["Amazon Elastic Compute Cloud - Compute"]},"CostTypes":{"IncludeTax":true,"IncludeSubscription":true,"UseBlended":false,"IncludeRefund":false,"IncludeCredit":true,"IncludeUpfront":true,"IncludeRecurring":true,"IncludeOtherSubscription":true,"IncludeSupport":true,"IncludeDiscount":true,"UseAmortized":false}}'
```

**CostTypes defaults:** `IncludeTax=true` (tax is on the invoice);
`IncludeSubscription=true` (Support, Marketplace); `UseBlended=false`
(Blended averages across linked accounts, masking overages);
`UseAmortized=false` for budget alerts, `true` for amortized RI/SP
analysis — pick one consistently.

**Zero-spend guardrail** (sandbox / new account): `BudgetLimit.Amount=0.01`,
`Unit=USD`. Then attach `ACTUAL > 50%` to SNS — a 50% threshold on a
$0.01 budget fires on the first dollar.

## Step 4 — Usage budget configuration (RI/SP utilization/coverage) (moved from SKILL.md)

```bash
# RI Utilization budget — alert when RI utilization drops below 80%
aws budgets create-budget --account-id 111111111111 \
  --budget '{"BudgetName":"ri-utilization-target","BudgetLimit":{"Amount":"80","Unit":"PERCENTAGE"},"TimeUnit":"MONTHLY","BudgetType":"RI_UTILIZATION"}'
# Savings Plan Coverage budget (latest GA feature) — same pattern with BudgetType SP_COVERAGE
```

**Usage budget constraints:** Usage budgets (`RI_*`, `SP_*`) do NOT
support budget actions (IAM/EC2/SSM). Only SNS/email/Slack
notifications. Set `ComparisonOperator` to `LESS_THAN_THRESHOLD` for
utilization/coverage targets — alerts fire when actual drops below the
target.

## Step 5 — Cost Anomaly Detection (monitor + subscription CLI) (moved from SKILL.md)

Cost Anomaly Detection is **separate from AWS Budgets** — it is a Cost
Explorer (CE) API. Provisioning requires two API calls.

```bash
# Service-level monitor (recommended over default account-wide)
aws ce create-anomaly-monitor \
  --anomaly-monitor '{"Name":"service-anomaly-monitor","Type":"DIMENSIONAL","MonitorDimension":"SERVICE"}'

# Subscription to SNS — anomaly > $100 publishes to topic
aws ce create-anomaly-subscription \
  --anomaly-subscription '{"Name":"prod-anomaly-subscription","Frequency":"DAILY","Threshold":100.0,"MonitorArn":"arn:aws:ce::111111111111:anomaly-monitor/default","Subscribers":[{"Address":"arn:aws:sns:us-east-1:111111111111:cost-anomaly-alerts","Type":"SNS"}]}'
```

The default account-wide monitor ARN is
`arn:aws:ce::<account-id>:anomaly-monitor/default`. Dimensional monitors
must be explicitly created. The topic policy must allow
`Principal: Service: ce.amazonaws.com` to `sns:Publish` — this is a
**different principal** from Budgets. Operators frequently reuse a
Budgets SNS topic for anomalies and wonder why anomaly alerts never
fire — the topic policy lacks the `ce.amazonaws.com` principal.
Frequency: `IMMEDIATE` (noisy); `DAILY` (batched, recommended);
`WEEKLY` (slow).

## Step 6 — Budget alerts (actual vs forecast CLI) (moved from SKILL.md)

```bash
# 80% ACTUAL — early warning (repeat for 90, 100; add 100% FORECAST)
aws budgets create-notification \
  --account-id 111111111111 --budget-name "prod-monthly-cost" \
  --notification '{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"}' \
  --subscribers Address=arn:aws:sns:us-east-1:111111111111:budget-alerts,Type=SNS
```

**Threshold types:** `PERCENTAGE` (relative to `BudgetLimit`, default)
or `ABSOLUTE_VALUE` (explicit dollar amount). Use `ABSOLUTE_VALUE` when
the threshold should not change if the budget limit changes.

**Actual vs Forecast:** `ACTUAL` is definitive; `FORECAST` is predictive
(uses trailing ~30 days). Pair them — forecast alone is unreliable in
the first 14 days of a budget period. **Usage budgets (RI_*, SP_*)**
support `ACTUAL` only — `FORECAST` is rejected by the API for non-COST
budget types.

## Step 7 — Budget actions (IAM role template + CLI) (moved from SKILL.md)

Budget actions require an **IAM role** that trusts `budgets.amazonaws.com`
and has permission for the action. This is the most commonly missed
prerequisite.

**IAM role template (trust + permission policy for APPLY_IAM_POLICY):**

```bash
# Trust policy MUST have Principal: Service: budgets.amazonaws.com
cat > /tmp/budget-actions-trust.json <<'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
"Principal":{"Service":"budgets.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF
# Permission policy grants: iam:AttachUserPolicy, iam:AttachRolePolicy,
# iam:DetachUserPolicy, iam:DetachRolePolicy, iam:ListAttached*Policies
aws iam create-role --role-name BudgetActionsRole \
  --assume-role-policy-document file:///tmp/budget-actions-trust.json
```

**Create the action — APPLY_IAM_POLICY at 100% ACTUAL:**

```bash
aws budgets create-budget-action \
  --account-id 111111111111 --budget-name "prod-monthly-cost" \
  --notification-type ACTUAL --action-type APPLY_IAM_POLICY \
  --action-threshold '{"ActionThresholdValue":100,"ActionThresholdType":"PERCENTAGE"}' \
  --definition '{"IamActionDefinition":{"PolicyArn":"arn:aws:iam::111111111111:policy/BudgetDenyAll","Roles":["SandboxAppRole"]}}' \
  --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionsRole \
  --approval-model AUTOMATIC
```

For EC2 stop, use `--action-type RUN_SSM_DOCUMENTS` with
`SsmActionDefinition.ActionSubType=STOP_EC2_INSTANCES` (or
`STOP_RDS_INSTANCE` for non-prod databases, 2024 GA).

**Action types:** `APPLY_IAM_POLICY` (attach policy to principals),
`REMOVE_IAM_POLICY` (detach — reverse an APPLY when budget resets),
`RUN_SSM_DOCUMENTS` (run SSM doc: `STOP_EC2_INSTANCES` /
`STOP_RDS_INSTANCE`).

**`ApprovalModel`:** `AUTOMATIC` (sandbox/dev — action fires on breach)
or `MANUAL` (production — requires human approval in the console).

**Cross-account constraint:** the `ExecutionRoleArn` MUST be in the same
account as the target resource. For a budget on a linked account that
stops EC2 in that linked account, the role must exist in the linked
account, not the payer.

## Step 8 — SNS topic + subscription + IAM policy (CLI) (moved from SKILL.md)

The SNS topic is the alerting backbone for both Budgets and Cost
Anomaly Detection. Provision it in `us-east-1`.

```bash
TOPIC_ARN=$(aws sns create-topic --name budget-alerts --region us-east-1 --query TopicArn --output text)

# Topic policy MUST allow BOTH budgets.amazonaws.com AND ce.amazonaws.com
cat > /tmp/budget-topic-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": ["budgets.amazonaws.com", "ce.amazonaws.com"]},
    "Action": "sns:Publish",
    "Resource": "$TOPIC_ARN"
  }]
}
EOF
aws sns set-topic-attributes --topic-arn "$TOPIC_ARN" \
  --attribute-name Policy --attribute-value file:///tmp/budget-topic-policy.json

aws sns subscribe --topic-arn "$TOPIC_ARN" --protocol email \
  --notification-endpoint finops@example.com
```

**Encrypted topic caveat:** if the topic uses SSE-KMS with a customer
CMK, the KMS key policy MUST grant `kms:GenerateDataKey*` and
`kms:Decrypt` to BOTH `budgets.amazonaws.com` and `ce.amazonaws.com`.
AWS-managed `alias/aws/sns` works out-of-the-box. Customer CMK without
the grant silently drops notifications — no error, no log. Email
subscriptions require the recipient to confirm; until confirmed,
`list-subscriptions-by-topic` shows `PendingConfirmation`.

## Step 10 — Verification (moved from SKILL.md)

```bash
aws budgets describe-budget --account-id 111111111111 --budget-name prod-monthly-cost
aws budgets describe-notifications-for-budget --account-id 111111111111 --budget-name prod-monthly-cost
aws budgets describe-budget-actions --account-id 111111111111 --budget-name prod-monthly-cost
aws budgets describe-budget-action-executions --account-id 111111111111 \
  --budget-name prod-monthly-cost \
  --time-period Start=2026-08-01T00:00:00Z,End=2026-08-10T23:59:59Z
aws ce get-anomaly-monitors
aws ce get-anomaly-subscriptions
aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:budget-alerts
aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:111111111111:budget-alerts
```
