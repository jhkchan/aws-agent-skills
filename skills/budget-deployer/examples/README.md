# End-to-End Example: AWS Budget Deployment

A walkthrough showing how to use the `budget-deployer` skill from
invocation through verification. Mirrors the structured-eval pattern of
shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production cost budget with an action tier. The
budget needs:

- Account-wide scope, $10,000 USD MONTHLY
- Alerts at 80/90/100% ACTUAL + 100% FORECAST to SNS
- APPLY_IAM_POLICY budget action at 100% ACTUAL (deny further spend on
  SandboxAppRole)
- Cost Anomaly Detection subscription on the default monitor, Threshold
  $100, DAILY to the same SNS topic

Budget name: `prod-monthly-cost`
Account: `111111111111`
Region: `us-east-1`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-budget
```

Then paste the requirements.

### Option B: Natural language

```
You: "Provision a production AWS Budget named prod-monthly-cost in
      account 111111111111. Budget amount $10,000 USD MONTHLY. Alerts
      at 80/90/100% ACTUAL and 100% FORECAST to SNS topic
      arn:aws:sns:us-east-1:111111111111:budget-alerts. Budget action:
      APPLY_IAM_POLICY (BudgetDenyAll on SandboxAppRole) at 100% ACTUAL,
      AUTOMATIC. ExecutionRoleArn
      arn:aws:iam::111111111111:role/BudgetActionsRole. Also wire Cost
      Anomaly Detection: default monitor, subscription
      prod-anomaly-subscription Threshold $100 DAILY to the same topic."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an aws budget"
```

Output:

```
[Phase: Deploy | Skills routed: budget-deployer]

Primary route: budget-deployer (score: 22)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
BUDGET: prod-monthly-cost in 111111111111 (account-wide)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Budget type: COST  | Scope: account-wide | Amount: $10,000 USD | MONTHLY
  [✓] Alerts: 80% / 90% / 100% ACTUAL + 100% FORECAST → SNS budget-alerts
  [✓] Budget actions: APPLY_IAM_POLICY (BudgetDenyAll on SandboxAppRole) at 100% ACTUAL, AUTOMATIC
  [✓] Action role: arn:aws:iam::111111111111:role/BudgetActionsRole (trust verified)
  [✓] SNS topic: arn:aws:sns:us-east-1:111111111111:budget-alerts (policy allows budgets + ce)
  [✓] SNS subscriptions: finops@example.com (confirmed), budget-auto-remediation Lambda
  [✓] KMS key policy: N/A (topic uses alias/aws/sns)
  [✓] Cost anomaly: default monitor + prod-anomaly-subscription (Threshold $100, DAILY, SNS)
  [✓] Cost filters: none
VERIFICATION_COMMANDS:
  aws budgets describe-budget --account-id 111111111111 --budget-name prod-monthly-cost
  aws budgets describe-notifications-for-budget --account-id 111111111111 --budget-name prod-monthly-cost
  aws budgets describe-budget-actions --account-id 111111111111 --budget-name prod-monthly-cost
  aws ce get-anomaly-monitors
  aws ce get-anomaly-subscriptions
  aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:budget-alerts
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# 1. Create the budget
aws budgets create-budget --account-id 111111111111 \
  --budget '{"BudgetName":"prod-monthly-cost","BudgetLimit":{"Amount":"10000","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST","CostTypes":{"IncludeTax":true,"IncludeSubscription":true,"UseBlended":false,"IncludeRefund":false,"IncludeCredit":true,"IncludeUpfront":true,"IncludeRecurring":true,"IncludeOtherSubscription":true,"IncludeSupport":true,"IncludeDiscount":true,"UseAmortized":false}}'

# 2. Attach notifications (80, 90, 100 ACTUAL + 100 FORECAST)
for pct in 80 90 100; do
  aws budgets create-notification --account-id 111111111111 \
    --budget-name prod-monthly-cost \
    --notification "{\"NotificationType\":\"ACTUAL\",\"ComparisonOperator\":\"GREATER_THAN\",\"Threshold\":${pct},\"ThresholdType\":\"PERCENTAGE\"}" \
    --subscribers Address=arn:aws:sns:us-east-1:111111111111:budget-alerts,Type=SNS
done
aws budgets create-notification --account-id 111111111111 \
  --budget-name prod-monthly-cost \
  --notification '{"NotificationType":"FORECAST","ComparisonOperator":"GREATER_THAN","Threshold":100,"ThresholdType":"PERCENTAGE"}' \
  --subscribers Address=arn:aws:sns:us-east-1:111111111111:budget-alerts,Type=SNS

# 3. Attach budget action (APPLY_IAM_POLICY at 100% ACTUAL)
aws budgets create-budget-action --account-id 111111111111 \
  --budget-name prod-monthly-cost \
  --notification-type ACTUAL --action-type APPLY_IAM_POLICY \
  --action-threshold '{"ActionThresholdValue":100,"ActionThresholdType":"PERCENTAGE"}' \
  --definition '{"IamActionDefinition":{"PolicyArn":"arn:aws:iam::111111111111:policy/BudgetDenyAll","Roles":["SandboxAppRole"]}}' \
  --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionsRole \
  --approval-model AUTOMATIC

# 4. Cost Anomaly Detection subscription
aws ce create-anomaly-subscription \
  --anomaly-subscription '{"Name":"prod-anomaly-subscription","Frequency":"DAILY","Threshold":100.0,"MonitorArn":"arn:aws:ce::111111111111:anomaly-monitor/default","Subscribers":[{"Address":"arn:aws:sns:us-east-1:111111111111:budget-alerts","Type":"SNS"}]}'
```

---

## Step 4 — Post-deployment verification

Run the verification commands from the checklist to confirm every
configuration was applied:

```bash
# Budget definition
aws budgets describe-budget --account-id 111111111111 --budget-name prod-monthly-cost

# Notifications attached (expect 4: 80/90/100 ACTUAL + 100 FORECAST)
aws budgets describe-notifications-for-budget --account-id 111111111111 --budget-name prod-monthly-cost

# Budget action (expect 1: APPLY_IAM_POLICY at 100% ACTUAL)
aws budgets describe-budget-actions --account-id 111111111111 --budget-name prod-monthly-cost

# Anomaly monitor + subscription
aws ce get-anomaly-monitors
aws ce get-anomaly-subscriptions

# SNS topic policy + subscriptions
aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:budget-alerts
aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:111111111111:budget-alerts
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Notification after budget | Often creates budget only — silent spend | Forces explicit `create-notification` per threshold | `create-budget` alone does NOT alert; operators will miss breaches until the invoice arrives |
| FORECAST pairing | Single 100% ACTUAL (fires late) | 80/90/100 ACTUAL + 100 FORECAST | FORECAST gives 6-10 day lead time vs ACTUAL |
| Action role trust | Uses any role ARN | Verifies trust on `budgets.amazonaws.com` | Without the trust, action fails at execution, not at create time |
| SNS topic principal | Single principal (`budgets.amazonaws.com`) | Both `budgets.amazonaws.com` AND `ce.amazonaws.com` | CE publishes as a different principal; silently drops anomaly alerts otherwise |
| Usage budget action | Attempts `create-budget-action` on RI/SP budget | Skips actions on usage budgets | API rejects — usage budgets support notifications only |
| Zero-spend amount | Sets `BudgetLimit.Amount=0` | Sets `0.01` | API rejects `0`; use `0.01` for zero-spend guardrail |

---

## Related artifacts

- **Skill definition:** `skills/budget-deployer/SKILL.md`
- **Provisioning CLI commands:** `skills/budget-deployer/references/provisioning-cli-commands.md`
- **Budget types + actions reference:** `skills/budget-deployer/references/budget-types-and-actions.md`
- **Slash command:** `commands/aws/deploy-budget.md`
- **Eval suite:** `skills/budget-deployer/evals/evals.json`
- **Legacy test cases:** `skills/budget-deployer/eval/test-cases.yaml`
