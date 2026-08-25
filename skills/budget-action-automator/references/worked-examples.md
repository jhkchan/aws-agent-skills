# Worked Examples (load on demand) — Budget Action Automator

Secondary worked examples and full CLI payloads moved verbatim from SKILL.md. Loaded on demand.

---

## Step 4 — Wire SNS notification (full CLI) (moved from SKILL.md)

For notify-only budgets (no enforcement):

```bash
# 1. Create the budget
aws budgets create-budget \
  --account-id 111111111111 \
  --budget '{
    "BudgetName": "monthly-cost-budget",
    "BudgetLimit": {"Amount": "10000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{
        "SubscriptionType": "SNS",
        "Address": "arn:aws:sns:us-east-1:111111111111:budget-alerts"
      }]
    }
  ]'
```

Create the SNS topic first with the right access policy:

```bash
aws sns create-topic --name budget-alerts
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:budget-alerts \
  --attribute-name Policy \
  --attribute-value '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "budgets.amazonaws.com"},
      "Action": "SNS:Publish",
      "Resource": "arn:aws:sns:us-east-1:111111111111:budget-alerts",
      "Condition": {"StringEquals": {"aws:SourceAccount": "111111111111"}}
    }]
  }'
```

**Common pitfall:** the SNS topic policy MUST allow
`budgets.amazonaws.com` to publish. A topic created without the
service principal produces silent notification failure — the budget
fires, the SNS publish is denied, and no alarm fires.

## Step 5 — Apply SCP deny for hard enforcement (full CLI) (moved from SKILL.md)

For Organization member accounts, the strongest enforcement is an
SCP attached on budget breach:

```bash
aws budgets put-budget-action \
  --account-id 111111111111 \
  --budget-name monthly-cost-budget \
  --notification-type ACTUAL \
  --action-type APPLY_SCP_FAMILY \
  --action-threshold '{"ActionThresholdValue": 100, "ActionThresholdType": "PERCENTAGE"}' \
  --definition '{
    "ScpActionDefinition": {
      "PolicyId": "p-abc123def456",
      "PolicyDocument": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Deny\",\"Action\":[\"ec2:RunInstances\",\"ecs:RegisterTaskDefinition\",\"lambda:CreateFunction\"],\"Resource\":\"*\"}]}"
    }
  }' \
  --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionExecutionRole \
  --approval-model AUTOMATIC
```

The SCP must already exist in Organizations — the budget action
ATTACHES it, it does not create it. Pre-create the SCP:

```bash
aws organizations create-policy \
  --type SERVICE_CONTROL_POLICY \
  --name "budget-breach-deny-new-resources" \
  --description "Attached automatically when monthly cost budget breaches 100%" \
  --content file://scp-deny-new-resources.json
```

Where `scp-deny-new-resources.json` contains the deny statement
above.

**The execution role trust policy MUST include
`budgets.amazonaws.com`:**

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "budgets.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

And the policy must include `organizations:AttachPolicy` and
`organizations:DetachPolicy` for the target root/OU/account.

## Step 6 — Apply IAM policy via budget action (full CLI) (moved from SKILL.md)

For per-user enforcement (restrict a specific IAM identity on
breach):

```bash
aws budgets put-budget-action \
  --account-id 111111111111 \
  --budget-name team-alpha-budget \
  --notification-type ACTUAL \
  --action-type APPLY_IAM_ACTION \
  --action-threshold '{"ActionThresholdValue": 100, "ActionThresholdType": "PERCENTAGE"}' \
  --definition '{
    "IamActionDefinition": {
      "PolicyArn": "arn:aws:iam::111111111111:policy/budget-restrict-policy",
      "Users": ["team-alpha-ci-bot"],
      "Groups": [],
      "Roles": []
    }
  }' \
  --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionExecutionRole \
  --approval-model AUTOMATIC
```

The IAM policy (`budget-restrict-policy`) typically denies
expensive actions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": [
      "ec2:RunInstances",
      "ec2:StartInstances",
      "sagemaker:CreateEndpoint",
      "lambda:CreateFunction"
    ],
    "Resource": "*"
  }]
}
```

The budget action attaches this policy to the listed user on breach.
Like SCP, it does NOT detach on recovery — wire a Lambda
(EventBridge-driven) to detach when the next month's budget resets.

## Step 13 — Forecast-based proactive action (full CLI) (moved from SKILL.md)

Forecast thresholds catch breaches 3-7 days before they happen:

```bash
aws budgets create-budget \
  --account-id 111111111111 \
  --budget '{
    "BudgetName": "monthly-cost-budget",
    "BudgetLimit": {"Amount": "10000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST"
  }' \
  --notifications-with-subscribers '[
    {
      "Notification": {
        "NotificationType": "FORECASTED",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 80,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{
        "SubscriptionType": "SNS",
        "Address": "arn:aws:sns:us-east-1:111111111111:budget-alerts"
      }]
    },
    {
      "Notification": {
        "NotificationType": "FORECASTED",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 90,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [{
        "SubscriptionType": "SNS",
        "Address": "arn:aws:sns:us-east-1:111111111111:budget-action-required"
      }]
    }
  ]'
```

**Forecast threshold rule of thumb:** set the forecast alert 10-15%
BELOW the actual enforcement threshold. Forecast at 85%, actual
enforcement at 100%. This gives a 3-7 day window to act.

## Worked example — REVIEW_REQUIRED (tag-scoped budget, tag not activated) (moved from SKILL.md)

### Worked example — REVIEW_REQUIRED (tag-scoped budget, tag not activated)

```text
BUDGET: env-prod-tag-scoped-budget
VERDICT: REVIEW_REQUIRED
CHECKLIST:
  [x] Budget type: COST (CostFilters: Tag=env:prod)
  [x] Monthly amount: 20000 USD (TimeUnit: MONTHLY)
  [x] Threshold: ACTUAL 90% (SNS notify)
  [x] Action: SNS_NOTIFY
  [ ] Cost allocation tags: NOT_ACTIVATED (tag 'env' is not active in Billing console — verified via `aws ce get-cost-and-usage --group-by Type=TAG,Key=env` returning only $NULL)
  [x] Multi-account scope: SINGLE
  [x] Approval model: N/A (notify-only)
  [x] Execution role: N/A (notify-only — no SCP/IAM action)
  [x] SCP detach on recovery: N/A
GAP: Cost allocation tag 'env' is NOT activated. The budget's CostFilters clause matches zero spend until the tag is activated, so the budget will never fire even at $1M of prod spend. Activate via `aws ce update-cost-allocation-tags-status --tag-keys env --status Active`, wait up to 24 hours for activation to take effect (historical data is NOT backfilled), then re-run this skill to emit AUTOMATION_DEPLOYED.
TEMPLATE: (held in draft — blocked until tag 'env' is activated)
```
