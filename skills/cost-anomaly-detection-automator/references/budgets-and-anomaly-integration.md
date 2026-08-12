# Budgets and Cost Anomaly Detection Integration Reference

Supplementary reference for the Cost Anomaly Detection Automator skill.
Use when integrating AWS Budgets with Cost Anomaly Detection, designing
hard-limit spend controls, or configuring Budget Actions.

## Cost Anomaly Detection vs AWS Budgets

| Dimension | Cost Anomaly Detection | AWS Budgets |
|---|---|---|
| Detection method | ML on historical spend patterns | Static threshold (operator-defined) |
| Sensitivity | Dynamic — adapts to spending trends | Fixed — does not adapt |
| Best for | Unexpected pattern deviations | Hard spend limits |
| Alert latency | 8-24 hours (daily evaluation cycle) | 8-24 hours (daily evaluation cycle) |
| False positive rate | Decreases over time with feedback | Zero — threshold is exact |
| Configuration | Monitor + Subscription (2 API calls) | Budget + Notification (1 API call) |
| Per-service granularity | Yes — dimension-based monitors | Yes — budget filters |
| Multi-account | Payer-level monitor | Payer-level budget |
| Auto-remediation | Lambda via SNS | Budget Actions (IAM, SSM, EC2 stop) |
| Cost | Free | Free (first 2 budgets); $0.01/budget/day thereafter |

**Key insight:** they are complementary, not redundant. Cost Anomaly
Detection catches "EC2 spend on Tuesday is 3x the usual pattern" even
if total spend is well under budget. Budgets catch "total monthly spend
exceeded $10K" even if the pattern looks normal. Use both for full
coverage.

## Budget types

| `BudgetType` | What it tracks | Example |
|---|---|---|
| `COST` | Total unblended cost | "Alert if spend > $10K/month" |
| `USAGE` | Specific usage unit | "Alert if EC2 hours > 10K/month" |
| `RI_UTILIZATION` | Reservation utilization % | "Alert if RI utilization < 90%" |
| `RI_COVERAGE` | Reservation coverage % | "Alert if RI coverage < 70%" |
| `SAVINGS_PLANS_UTILIZATION` | SP utilization % | "Alert if SP utilization < 95%" |
| `SAVINGS_PLANS_COVERAGE` | SP coverage % | "Alert if SP coverage < 80%" |

## Budget notification types

| `NotificationType` | When it fires | Use case |
|---|---|---|
| `ACTUAL` | Actual spend crosses threshold | "We already spent 80% of budget" |
| `FORECASTED` | Forecasted spend crosses threshold | "We're projected to exceed budget" |

**Best practice:** always configure BOTH actual and forecasted alerts.
Actual tells you "it happened." Forecasted gives you lead time to act.

## Budget Actions (2024-2025 GA)

Budget Actions execute IAM policy application, SSM Automation, or EC2
instance stop when a budget threshold is breached. This provides a
hard-limit remediation path.

| Action type | What it does | Use case |
|---|---|---|
| `APPLY_IAM_POLICY` | Apply a restrictive IAM policy | Deny resource creation at budget breach |
| `RUN_SSM_DOCUMENTS` | Execute SSM Automation runbook | Right-size or stop resources |
| `RUN_AUTOMATION` | Trigger SSM Automation | Same as above with broader scope |

Budget Action creation:

```bash
aws budgets create-budget-action \
  --account-id 111111111111 \
  --budget-name monthly-cost-budget \
  --notification-type ACTUAL \
  --action-type APPLY_IAM_POLICY \
  --action-threshold '{"ActionThresholdValue": 100.0, "ActionThresholdType": "PERCENTAGE"}' \
  --definition '{"IamActionDefinition":{"PolicyArn":"arn:aws:iam::111111111111:policy/budget-stop-creation"}}' \
  --approval-model AUTOMATIC \
  --subscribers '[{"SubscriptionType":"SNS","Address":"arn:aws:sns:us-east-1:111111111111:budget-action-alerts"}]'
```

**Safety note:** Budget Actions with `APPROVAL_MODEL: AUTOMATIC` fire
without human approval. A misconfigured action that applies a deny-all
IAM policy at 100% budget can lock out all IAM users. Always test with
`APPROVAL_MODEL: MANUAL` first.

## Integration pattern

The recommended integration for full cost protection:

```
                     ┌─────────────────────────────┐
                     │    AWS Cost Explorer Data    │
                     └─────────┬─────────┬─────────┘
                               │         │
              ┌────────────────┘         └────────────────┐
              ▼                                           ▼
  ┌──────────────────────┐                  ┌──────────────────────┐
  │ Cost Anomaly Monitor  │                  │    AWS Budget         │
  │  (ML-based detection) │                  │  (Static thresholds)  │
  └──────────┬───────────┘                  └──────────┬───────────┘
             │                                          │
             ▼                                          ▼
  ┌──────────────────────┐                  ┌──────────────────────┐
  │ Anomaly Subscription │                  │ Budget Notification   │
  │ (SNS -> Lambda)      │                  │ (SNS / Email)         │
  └──────────┬───────────┘                  └──────────┬───────────┘
             │                                          │
             ▼                                          ▼
  ┌──────────────────────┐                  ┌──────────────────────┐
  │ Lambda Router        │                  │ Budget Action        │
  │ (severity routing,   │                  │ (IAM/SSM/EC2 stop)   │
  │  Slack, tag/remediate)│                 │ (hard limit)         │
  └──────────────────────┘                  └──────────────────────┘
```

- **Anomaly Detection** catches pattern deviations and routes to Lambda
  for soft remediation (tag, notify, right-size).
- **Budgets** catch hard-limit breaches and execute Budget Actions for
  hard enforcement (deny creation, stop instances).

## Verification queries

### List all budgets

```bash
aws budgets describe-budgets \
  --account-id 111111111111 \
  --query 'Budgets[].[BudgetName,BudgetLimit.Amount,BudgetLimit.Unit,TimeUnit,BudgetType]' \
  --output table
```

### List budget notifications

```bash
aws budgets describe-notifications-for-budget \
  --account-id 111111111111 \
  --budget-name monthly-cost-budget
```

### List budget actions

```bash
aws budgets describe-budget-actions \
  --account-id 111111111111 \
  --budget-name monthly-cost-budget
```

## Common pitfalls

### Budget created but no notification

`create-budget` creates the budget. Notifications are added via
`--notifications-with-subscribers` (at creation time) or
`create-notification` (post-creation). A budget without notifications
silently tracks spend without alerting.

### Threshold type confusion

`ThresholdType: PERCENTAGE` is relative to the budget limit. `ThresholdType:
ABSOLUTE_VALUE` is a raw dollar amount. A threshold of 80 with
`PERCENTAGE` on a $10K budget alerts at $8K. The same threshold with
`ABSOLUTE_VALUE` alerts at $80.

### Budget action execution role

Budget Actions assume a service role to execute IAM/SSM/EC2 actions. A
missing or misconfigured role produces `FAILED` action status. Verify
the role has `iam:PutUserPolicy`, `ssm:StartAutomationExecution`, or
`ec2:StopInstances` as appropriate.

### Budget cost filter

Budgets can be scoped by service, linked account, tag, or cost category.
A budget scoped to `SERVICE=EC2` does NOT alert on S3 spend. Verify the
budget filter covers the intended spend scope.
