# End-to-end usage scenario: budgets-auditor

A walkthrough showing the skill auditing an account whose single budget has
both a silent SNS delivery failure (CONFIG_GAP, Step 3) and a single-
threshold/no-forecast gap (Steps 4-5), demonstrating how the verdict
aggregates, why the SNS policy gap is the worst finding, and the additive
remediation workflow.

## Input (user prompt)

> We configured a budget but the alerts never arrive. Audit our spend
> posture before the monthly billing review.

```json
{
  "Budgets": [
    {
      "BudgetName": "monthly-total",
      "BudgetType": "COST",
      "TimeUnit": "MONTHLY",
      "BudgetLimit": {"Amount": "15000.0", "Unit": "USD"},
      "CostTypes": {"IncludeTax": true, "UseAmortized": false, "IncludeDiscount": true},
      "CalculatedSpend": {
        "ActualSpend": {"Amount": "9800.0", "Unit": "USD"},
        "ForecastedSpend": {"Amount": "16400.0", "Unit": "USD"}
      }
    }
  ]
}
```

Notifications for "monthly-total":

```json
{
  "Notifications": [
    {
      "NotificationType": "ACTUAL",
      "Notification": {
        "NotificationType": "ACTUAL",
        "ComparisonOperator": "GREATER_THAN",
        "Threshold": 100.0,
        "ThresholdType": "PERCENTAGE"
      },
      "Subscribers": [
        {"SubscriptionType": "SNS", "Address": "arn:aws:sns:us-east-1:777777777777:budget-alerts"}
      ]
    }
  ]
}
```

SNS topic policy for arn:aws:sns:us-east-1:777777777777:budget-alerts:

```json
{
  "Version": "2008-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::777777777777:root"},
      "Action": "SNS:Publish",
      "Resource": "arn:aws:sns:us-east-1:777777777777:budget-alerts"
    }
  ]
}
```

## Skill output

```text
ACCOUNT: 777777777777
VERDICT: CONFIG_GAP
REASON: Budget "monthly-total" has a 100% ACTUAL notification wired to an SNS
topic whose policy omits the budgets.amazonaws.com publish principal — alerts
are dispatched by Budgets but silently rejected at SNS delivery (Step 3). The
single 100% ACTUAL threshold also leaves no reaction time and there is no
FORECASTED notification despite the forecast ($16400) exceeding the limit
($15000) (Steps 4-6).
FINDINGS:
  - [HIGH] monthly-total: SNS topic arn:aws:sns:us-east-1:777777777777:budget-alerts
    policy lacks budgets.amazonaws.com sns:Publish — notification dispatched but
    rejected at delivery; zero console error (Step 3)
  - [MEDIUM] monthly-total: single threshold at 100% ACTUAL — no early-warning
    tier below 80% (Step 4)
  - [MEDIUM] monthly-total: no FORECASTED notification — ACTUAL-only alert
    arrives after spend is incurred plus 8-14h cost-data lag (Step 5)
  - [MEDIUM] monthly-total: ForecastedSpend $16400 > BudgetLimit $15000 with no
    FORECASTED notification to alert on the on-track breach (Step 6)
  - [OK] monthly-total: budget exists and is not yet actually breached ($9800
    vs $15000)
REMEDIATION:
  1. HIGH — Add the budgets service principal to the SNS topic policy:
     aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:777777777777:budget-alerts
       --region us-east-1 --query 'Attributes.Policy' --output text > /tmp/budget-topic-backup.json
     (back up first), then add a statement:
       {Effect: Allow, Principal: {Service: budgets.amazonaws.com},
        Action: SNS:Publish, Resource: <topic-arn>}
     and apply via aws sns set-topic-attributes --topic-arn <arn>
       --attribute-name Policy --attribute-value <updated-policy>.
  2. MEDIUM — Add a FORECASTED notification at 80%: aws budgets
     create-notification --account-id 777777777777 --budget-name monthly-total
     --notification NotificationType=FORECASTED,... --subscribers ... .
  3. MEDIUM — Add an early-warning ACTUAL notification at 50%.
  4. Confirm total notifications on monthly-total stay <= 11 (quota).
```

## What the skill caught that a generic assistant misses

1. **The silent SNS delivery failure.** A generic assistant sees the SNS topic
   policy grants the account root and says "looks reasonable." The skill
   recognises that AWS Budgets publishes as the `budgets.amazonaws.com`
   service principal — NOT as the account root. The root principal grant is
   irrelevant; without the service principal, the notification is dispatched
   by Budgets and rejected by SNS with zero console error. This is the #1
   reason budget alerts "don't work" in production.

2. **The cost-data lag argument for FORECASTED.** A generic assistant may
   note the single threshold is "fine." The skill explains that cost actuals
   trail real spend by 8-14 hours, so a 100% ACTUAL alert arrives after the
   budget is already breached. Only a FORECASTED notification provides lead
   time — and here the forecast ($16400) already exceeds the limit ($15000),
   so a FORECASTED notification would have fired by now if it existed.

3. **The 11-notification quota.** A generic assistant proposes adding "more
   alerts." The skill flags that each budget is capped at 11 notifications
   (hard limit) and counts existing notifications before proposing additions
   so the `CreateNotification` call does not fail with
   `LimitExceededException`.

4. **Additive remediation ordering.** The skill backs up the SNS topic policy
   before modifying it (topic policies are unversioned — a bad statement
   breaks ALL topic publishers, not just Budgets) and prefers adding a
   statement over rewriting the policy.

## Slash-command invocation

```
/aws:audit-budgets
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit our budgets before the billing review — alerts aren't arriving"
```

The orchestrator emits
`[Phase: Audit | Skills routed: budgets-auditor]` and hands off to this skill
for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit my AWS budgets"
# [Phase: Audit | Skills routed: budgets-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the policy and notifications, validate the budget posture:

```bash
# Verify the budgets principal is now in the topic policy
aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:777777777777:budget-alerts \
  --profile default --region us-east-1 --query 'Attributes.Policy' --output text | jq '.Statement[].Principal'

# Confirm the new FORECASTED notification was created
aws budgets describe-notifications-for-budget --account-id 777777777777 \
  --budget-name monthly-total --profile default --region us-east-1

# Check that the next threshold crossing produces a CloudTrail Publish event
# from budgets.amazonaws.com (forensic confirmation that delivery now works)
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=Publish \
  --profile default --region us-east-1 | jq '.Events[] | select(.Username | contains("budgets"))'
```

Then monitor the budget for one threshold cycle to confirm delivery.
