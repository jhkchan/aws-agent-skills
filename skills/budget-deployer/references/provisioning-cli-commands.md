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
