---
name: budget-action-automator
description: Designs and deploys AWS Budgets automated actions — cost, usage, RI coverage, and RI utilization budgets with threshold-driven responses. Covers budget creation (actual vs forecasted alerts), SNS notification wiring, IAM action attachment (apply SCP deny on breach, apply IAM policy to constrain usage), EventBridge routing to Lambda for custom remediation (stop non-prod EC2, tag untagged resources, post to Slack), multi-account rollout via Organizations Payer, cost allocation tag enforcement as a budget prerequisite, Budgets API automation patterns, forecast-based proactive action before actual breach, and budget rollover/reset semantics. Emits AUTOMATION_DEPLOYED with a workflow template (CloudFormation / CLI) or REVIEW_REQUIRED with the specific gap. Use when building budget actions, wiring IAM or SCP responses to budget breaches, or complementing Cost Anomaly Detection with threshold-based controls.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline workflow design. Live deployment uses aws budgets create-budget, create-notification, subscribe, put-budget-action, describe-budget-action, aws ce get-cost-and-usage, get-cost-forecast, aws organizations attach-policy, create-policy, aws sns create-topic — AWS CLI v2, SSO or key-based credentials.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: FinOps
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Designing AWS Budgets automated actions, wiring IAM/SCP responses to budget breaches, building multi-account budget rollouts via Organizations Payer, enforcing cost allocation tags before budget creation, complementing Cost Anomaly Detection with threshold controls, configuring forecast-based proactive action, or automating RI coverage / RI utilization budgets.
  activation_triggers: automate budget action, put-budget-action, budget breach SCP, budget SNS notification, forecast budget action, RI coverage budget, RI utilization budget, budget multi-account payer, cost allocation tag budget, Budgets API automation, budget EventBridge Lambda, budget Slack notification
  invocation_schema: 'Input: either (a) a budget requirement ("alert at 80% of $10K monthly cost budget and deny new EC2 launches at 100%"), OR (b) a budget configuration under review. Output: deterministic BUDGET ACTION block per budget — BUDGET/THRESHOLD/NOTIFICATION/RESPONSE/ MULTI_ACCOUNT/VERDICT — where VERDICT is AUTOMATION_DEPLOYED (workflow template ready) or REVIEW_REQUIRED (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Budgets, budget action, put-budget-action, SCP deny, SNS notification, cost budget, usage budget, RI coverage, RI utilization, forecast threshold, Cost Anomaly Detection, cost allocation tags, Organizations Payer, budget rollover, EventBridge budget, FinOps automation
  tags: aws-budgets, finops, cost-optimization, scp, iam-action, eventbridge, automate
---

# Budget Action Automator

## Mindset

**One-line takeaway:** every budget action is a four-stage pipeline —
**define** (budget type, amount, period) → **threshold** (actual and/or
forecasted, with the right comparison) → **notify** (SNS, email, Slack
via Lambda) → **respond** (IAM/SCP action for hard enforcement, or
EventBridge → Lambda for custom remediation). A gap in ANY stage
produces a silent failure: the budget fires but no one hears it, or
the notification arrives after spend already blew past the limit.

- **Budget type** without the right **threshold type** is noise: a
  cost budget alerted only on `ACTUAL` misses the chance to act
  before the money is spent. Forecast thresholds catch trends 3-7
  days before actual breach.
- **Notification** without **response** is reporting, not control.
  SNS to an email queue is a post-mortem; SCP deny on the OU is
  prevention of further spend.
- **SCP deny is the only hard enforcement primitive in Budgets.** A
  budget action with `ActionType: APPLY_SCP` (formerly
  `APPLY_POLICY`) blocks new resource creation in the target account
  or OU. It does NOT shut down already-running resources — pair it
  with EventBridge → Lambda → `stop-instances` for full enforcement.

## Quick navigation

| You want to... | Go to |
|---|---|
| Pick a budget type (cost/usage/RI coverage/RI utilization) | Step 2 |
| Choose actual vs forecasted threshold | Step 3 |
| Wire SNS notification | Step 4 |
| Apply SCP deny for hard enforcement | Step 5 |
| Apply IAM policy via budget action | Step 6 |
| EventBridge → Lambda for custom action | Step 7 |
| Stop non-prod EC2 on breach | Step 8 |
| Tag untagged resources via budget | Step 9 |
| Slack notification via Lambda | Step 10 |
| Multi-account via Organizations Payer | Step 11 |
| Cost allocation tag prerequisite | Step 12 |
| Forecast-based proactive action | Step 13 |
| Budget vs Cost Anomaly Detection | Step 14 |
| Budget rollover / reset semantics | Step 15 |
| Common destructive-change pitfalls | Anti-Patterns |

## Critical rules at a glance (do NOT bury these)

1. **`put-budget-action` with `APPLY_SCP` only attaches the policy;
   it does NOT retroactively constrain resources.** It also requires
   the budget action to be in an account that is a member of an
   Organization, and the target must be the account itself or an OU
   it belongs to. A standalone account cannot use SCP actions.
2. **Forecast thresholds (`FORECASTED`) are probabilistic.** AWS
   forecast models are 80% confidence intervals by default. A
   forecast alert at 100% of budget may fire when actual spend is
   only at 70%. Always pair forecast with a higher actual threshold
   to avoid premature action.
3. **Cost allocation tags MUST be activated in the Billing console
   before any budget that uses `CostFilters` (e.g., by `env`,
   `team`, `project`) will work.** A budget with
   `CostFilters: {Tag: [env:prod]}` against a tag that is not
   activated produces zero matched spend — the budget never fires.
4. **Budget actions (`put-budget-action`) are distinct from
   notifications (`create-notification` + `subscribe`).** A
   notification sends an SNS/email message; an action runs IAM/SCP
   or both. Many operators wire notification and assume enforcement
   is in place.
5. **RI coverage and RI utilization budgets do NOT respond to
   on-demand spend directly.** They measure commitment performance.
   A 70% RI coverage budget at 65% actual coverage fires regardless
   of total dollar spend — useful for ensuring commitment
   compliance, not for cost control.

## Pre-flight: data requirements

Designing a budget action requires these inputs:

| Input | Source | Why |
|---|---|---|
| Budget type | Cost / Usage / RI Coverage / RI Utilization | Drives the `BudgetType` field |
| Budget amount + time unit | Customer-specified or derived from CE | `BudgetLimit.Amount` + `TimeUnit` |
| Cost filters (optional) | Tag, LinkedAccount, Service, etc. | `CostFilters` for scoped budgets |
| Notification thresholds | Customer-specified % of budget | Drives `Notification.Threshold` + `ThresholdType` |
| Response type | Notify only / IAM / SCP / Lambda | Drives `ActionType` |
| Account structure | `organizations list-roots`, `list-organizational-units` | SCP target for multi-account |
| SNS topic ARN | `sns create-topic` | Notification destination |
| Cost allocation tags status | `ce get-cost-and-usage` (TagKey filter) | Verify tags are activated before scoping |
| Existing budgets | `budgets describe-budgets` | Avoid overwriting |

**If the input is malformed** (missing budget amount, ambiguous
budget type), emit:

```text
BUDGET: <reference>
VERDICT: ERROR
REASON: Cannot design budget action — budget type, amount, and time unit are required.
GAP: Re-supply the budget requirement with explicit type (cost/usage/RI coverage/RI utilization), dollar or unit amount, and monthly/quarterly/annual period.
```

## Process — Workflow design (apply in order)

### Step 0: Expert knowledge — non-obvious Budgets behaviors

These behaviors change the workflow design if ignored:

- **`put-budget-action` is a newer API replacing `create-notification`
  + `subscribe` for actionable budgets.** Notifications still work
  for SNS-only flows; actions add the IAM/SCP layer. Mixing the two
  on the same budget produces duplicate SNS messages and conflicting
  state.

- **`APPLY_SCP_FAMILY` (formerly `APPLY_POLICY`) attaches an SCP to
  the account or OU.** It does NOT detach on budget recovery. The
  SCP must be explicitly removed (`delete-policy`) or have a
  condition statement with `aws:BudgetThreshold` that auto-relaxes.
  Most teams forget the detach step and the account remains locked
  past the budget period.

- **AWS Budgets evaluates every 8-12 hours.** It is NOT real-time.
  A budget set at 100% with no forecast threshold can let spend
  climb to 130% before the action fires. Forecast thresholds with a
  `PERCENTAGE` of 80-90% are the only reliable prevention mechanism.

- **Cost Explorer (CE) data lags 12-24 hours.** Budget calculations
  depend on CE. A budget breach today reflects spend from yesterday
  — the action fires against stale data.

- **`ThresholdType: PERCENTAGE` is against the `BudgetLimit`.** It is
  NOT against the previous month. A 100% threshold on a $10K budget
  fires at $10K, regardless of whether last month was $5K or $20K.

- **Budget actions support a `Definition` block with
  `IamActionDefinition`, `ScpActionDefinition`, and
  `SsmActionDefinition`.** SSM action definition is the most recent
  addition — it lets a budget action trigger an SSM Automation
  runbook directly (no EventBridge middle layer). Useful for
  stop-instances workflows.

- **Budgets are per-account by default.** A budget created in the
  payer account does NOT cascade to member accounts. To enforce
  per-member spend limits, create a budget per LinkedAccount using
  `CostFilters: {LinkedAccount: [<member-account-id>]}` in the
  payer, or deploy the budget via a StackSet to each member.

- **`CostBudgets` track blended and unblended cost.** `BudgetType:
  COST` uses unblended cost by default. Refunds, credits, and
  upfront RI fees affect the calculation differently than the CE
  console — verify with `describe-budget` after creation.

- **`RI_UTILIZATION` and `RI_COVERAGE` budgets use the same API but
  different `BudgetType` values.** Utilization measures "are we
  using RIs we bought" (target: 100%); coverage measures "what %
  of compute is RI-covered" (target: business-defined, often 70-85%).

- **A budget action `ExecutionRole` is required for IAM/SCP actions.**
  The role must trust `budgets.amazonaws.com` and have permissions
  for the action (`iam:AttachUserPolicy`, `organizations:AttachPolicy`).
  A missing or misconfigured execution role produces silent failure
  — the action is in `ERROR` state but no alarm fires.

### Step 1: Classify the budget goal

For each budget requirement, classify the goal:

| Goal | Budget type | Example | Notes |
|---|---|---|---|
| Cost containment | `COST` | "$10K/month total spend" | Most common; tracks unblended cost |
| Usage tracking | `USAGE` | "10,000 EC2 hours/month" | Useful for free-tier guardrails |
| Commitment performance | `RI_COVERAGE` | "75% RI coverage for EC2" | Drives commitment strategy |
| Commitment efficiency | `RI_UTILIZATION` | "95% RI utilization" | Detects unused RIs |
| Savings Plan coverage | `SAVINGS_PLANS_COVERAGE` | "80% SP coverage" | Modern alternative to RI |
| Savings Plan utilization | `SAVINGS_PLANS_UTILIZATION` | "95% SP utilization" | Detects unused SPs |

If the goal is "stop over-spend," use `COST`. If the goal is "ensure
we use what we committed," use `RI_UTILIZATION` or
`SAVINGS_PLANS_UTILIZATION`. If the goal is "ensure we commit enough
to cover our footprint," use `RI_COVERAGE` or
`SAVINGS_PLANS_COVERAGE`.

### Step 2: Pick the budget type and time period

| Time unit | Use case | Reset behavior |
|---|---|---|
| `MONTHLY` | Most operational budgets | Resets on the 1st (calendar month) |
| `QUARTERLY` | Capex / project budgets | Resets at the start of each quarter |
| `ANNUALLY` | Fiscal-year budgets | Resets on the configured start date |
| `DAILY` | High-resolution guardrails | Resets at 00:00 UTC |

**Budget rollover is NOT native.** AWS Budgets reset to zero at the
start of each period — they do NOT carry forward unused budget. For
"quarterly capex that rolls over," track it in a separate system
(e.g., a Lambda that stores the delta in DynamoDB) and use the
Lambda to gate the budget action rather than relying on
`BudgetLimit`.

### Step 3: Choose the threshold type (the threshold matrix)

| Threshold type | When it fires | Use case |
|---|---|---|
| `ACTUAL` | When actual spend crosses the threshold | Late-stage alerting; cannot prevent breach |
| `FORECASTED` | When forecasted end-of-period spend crosses threshold | Proactive; 3-7 day warning before breach |
| Combined (ACTUAL 100% + FORECASTED 90%) | Both | Recommended for production budgets |

**Decision rule:** default to **both** `FORECASTED` at 80% (warning)
and 90% (action), plus `ACTUAL` at 100% (hard enforcement). For
non-critical budgets, `ACTUAL` at 100% alone is acceptable.

Forecast thresholds in detail:

```text
FORECASTED @ 80% → SNS notify (Slack/email — human attention)
FORECASTED @ 90% → SNS + IAM policy (restrict IAM user)
ACTUAL     @ 100% → SCP deny (block new resource creation)
ACTUAL     @ 110% → EventBridge → Lambda → stop non-prod EC2
```

### Step 4: Wire SNS notification

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

### Step 5: Apply SCP deny for hard enforcement

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

### Step 6: Apply IAM policy via budget action

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

### Step 7: EventBridge → Lambda for custom action

For actions beyond IAM/SCP (stop instances, tag resources, post to
Slack), use EventBridge. The Budgets service emits events to
EventBridge on notification:

```bash
aws events put-rule \
  --name budget-breach-custom-action \
  --event-pattern '{
    "source": ["aws.budgets"],
    "detail-type": ["Budget Notification"],
    "detail": {
      "NotificationType": ["ACTUAL"],
      "Action": ["None"]
    }
  }'

aws events put-targets \
  --rule budget-breach-custom-action \
  --targets '[{"Id":"budget-action-lambda","Arn":"arn:aws:lambda:us-east-1:111111111111:function:budget-breach-handler","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:budget-action-dlq"}}]'
```

Lambda handler pattern:

```python
import boto3, json, os

ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')

def lambda_handler(event, context):
    budget_name = event['detail']['BudgetName']
    threshold = event['detail']['Threshold']

    if threshold >= 110:
        # Stop non-prod EC2
        instances = ec2.describe_instances(Filters=[
            {'Name': 'tag:env', 'Values': ['dev', 'staging']}
        ])
        instance_ids = [i['InstanceId'] for r in instances['Reservations'] for i in r['Instances']]
        if instance_ids:
            ec2.stop_instances(InstanceIds=instance_ids)

    # Post to Slack
    ssm.send_command(
        InstanceIds=[],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': [f'curl -X POST -H "Content-type: application/json" --data \'{{"text":"Budget {budget_name} breached at {threshold}%"}}\' {os.environ["SLACK_WEBHOOK"]}'}
    )

    return {'statusCode': 200}
```

**Trade-off table:**

| Dimension | Native budget action | EventBridge + Lambda |
|---|---|---|
| IAM/SCP enforcement | Native, low-latency | Possible but requires Lambda AssumeRole |
| Custom logic (stop EC2, Slack) | Not supported | Full Lambda power |
| Built-in retry | `ApprovalModel: AUTOMATIC` | Configure manually (Lambda async config) |
| Audit | CloudTrail on `budgets:PutBudgetAction` | CloudTrail on Lambda invocations |
| Idempotency | Budgets deduplicates per period | Consumer's responsibility |

### Step 8: Stop non-prod EC2 on budget breach

A common enforcement: when budget breaches 110%, stop all `env=dev`
and `env=staging` EC2 instances. This is NOT a native budget action
— it requires EventBridge → Lambda (Step 7) OR the newer SSM Action
definition:

```bash
aws budgets put-budget-action \
  --account-id 111111111111 \
  --budget-name monthly-cost-budget \
  --notification-type ACTUAL \
  --action-type APPLY_SSM_ACTION \
  --action-threshold '{"ActionThresholdValue": 110, "ActionThresholdType": "PERCENTAGE"}' \
  --definition '{
    "SsmActionDefinition": {
      "ActionSubType": "STOP_EC2_INSTANCES",
      "Region": "us-east-1",
      "InstanceIds": ["i-0abc123def456"]
    }
  }' \
  --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionExecutionRole \
  --approval-model AUTOMATIC
```

**SSM Action limitations:**
- Static instance IDs only — no tag-based targeting
- Single-region
- Start instances on recovery requires a separate action
- For tag-based or multi-region workflows, use EventBridge + Lambda

### Step 9: Tag untagged resources via budget action

For tag-compliance budgets (e.g., "all resources must have `env`
tag"), the budget detects non-compliance and the action triggers
SSM Automation to apply default tags:

```bash
# Tag compliance budget (uses CostFilters)
aws budgets create-budget \
  --account-id 111111111111 \
  --budget '{
    "BudgetName": "untagged-resource-budget",
    "BudgetLimit": {"Amount": "0", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
      "Tag": ["env:$NULL"]
    }
  }'
```

Then wire EventBridge → Lambda → SSM `AWS-TagResource`:

```python
# Lambda: detect untagged resources via Resource Groups Tagging API
import boto3
rgta = boto3.client('resourcegroupstaggingapi')

def lambda_handler(event, context):
    resp = rgta.get_resources(TagFilters=[{'Key': 'env', 'Values': []}])
    for resource in resp['ResourceTagMappingList']:
        if not any(t['Key'] == 'env' for t in resource['Tags']):
            rgta.tag_resources(
                ResourceARNList=[resource['ResourceARN']],
                Tags={'env': 'unknown', 'needs-tag-review': 'true'}
            )
    return {'statusCode': 200}
```

**Tagging budgets only work if cost allocation tags are activated
(Step 12).** Without activation, the budget's `CostFilters: Tag`
clause matches nothing.

### Step 10: Slack notification via Lambda

Native SNS notifications do not include Slack formatting. Wire SNS →
Lambda → Slack:

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:budget-alerts \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:111111111111:function:budget-slack-forwarder
```

Lambda handler:

```python
import boto3, json, os, urllib3
http = urllib3.PoolManager()

def lambda_handler(event, context):
    message = json.loads(event['Records'][0]['Sns']['Message'])
    text = (f":rotating_light: *Budget Alert*\n"
            f"Budget: {message.get('BudgetName', 'unknown')}\n"
            f"Threshold: {message.get('Threshold', 'unknown')}% ({message.get('NotificationType', 'unknown')})\n"
            f"Actual: ${message.get('ActualSpend', {}).get('Amount', 'unknown')}\n"
            f"Forecast: ${message.get('ForecastedSpend', {}).get('Amount', 'unknown')}")
    http.request('POST', os.environ['SLACK_WEBHOOK'], body=json.dumps({'text': text}))
    return {'statusCode': 200}
```

### Step 11: Multi-account via Organizations Payer

For fleet-wide budget enforcement, deploy budgets from the Payer
account:

```bash
# In the Payer account — budget per LinkedAccount
aws budgets create-budget \
  --account-id <payer-account-id> \
  --budget '{
    "BudgetName": "team-alpha-prod-budget",
    "BudgetLimit": {"Amount": "50000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {
      "LinkedAccount": ["111111111111"]
    }
  }'
```

For per-member-account enforcement (budget lives in each member):

```bash
# StackSet deployment
aws cloudformation create-stack-set \
  --stack-set-name budget-per-member \
  --template-body file://budget-template.yaml \
  --permission-model SERVICE_MANAGED \
  --capabilities CAPABILITY_IAM \
  --auto-deployment 'Enabled=true,RetainStacksOnAccountRemoval=false'

aws cloudformation create-stack-instances \
  --stack-set-name budget-per-member \
  --deployment-targets 'OrganizationalUnitIds=["ou-abc-123def456"]' \
  --regions us-east-1
```

**Multi-account scoping techniques:**

| Technique | Scope | Use case |
|---|---|---|
| `CostFilters: LinkedAccount` in payer | Single member | Per-team budget, payer-side enforcement |
| StackSet to OU | All members in OU | Standard budget per account |
| SCP at the OU level on breach | All members in OU | Fleet-wide hard lock |
| Tag-based budget in payer | Cross-account tag scope | "All prod resources across all accounts" |

### Step 12: Cost allocation tag enforcement (BEFORE budget)

Cost allocation tags MUST be activated before any tag-scoped budget
works:

```bash
# Check activated tags
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-07-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=env
```

If the result returns no rows or only `$NULL`, the tag is not
activated. Activate:

```bash
aws ce update-cost-allocation-tags-status \
  --tag-keys env team project \
  --status Active
```

Activation takes up to 24 hours to take effect, and historical data
is NOT backfilled — only future spend is matched.

### Step 13: Forecast-based proactive action

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

### Step 14: Budget vs Cost Anomaly Detection — complementary use

AWS Budgets and AWS Cost Anomaly Detection (CAD) solve DIFFERENT
problems. Use both:

| Dimension | AWS Budgets | Cost Anomaly Detection |
|---|---|---|
| Detection type | Threshold-based (predicted or actual) | ML-based (deviation from baseline) |
| Latency | 8-12 hours | 24+ hours |
| Action | Native (SCP, IAM, SSM, SNS) | Anomaly subscription (SNS only) |
| Use case | Known spend limits | Unknown spend patterns |
| Example | "$10K/month, alert at 80%" | "Spend on Bedrock spiked 5x unexpectedly" |

**Complementary pattern:**
- Budget: enforces known limits (monthly cost cap, RI coverage
  target)
- CAD: catches unknown anomalies (sudden service spike, unauthorized
  resource launch, misconfigured retry loop)

Wire CAD subscriptions to a different SNS topic than budget alerts
to keep the audit trail separate.

### Step 15: Budget rollover / reset semantics

AWS Budgets do NOT roll over. Each period resets to zero. For
rollover requirements:

```python
# Lambda running daily, storing rollover in DynamoDB
import boto3, os
from datetime import datetime
dynamodb = boto3.resource('dynamodb')
budgets = boto3.client('budgets')
table = dynamodb.Table(os.environ['ROLLOVER_TABLE'])

def lambda_handler(event, context):
    resp = budgets.describe_budget(
        AccountId=os.environ['ACCOUNT_ID'],
        BudgetName=os.environ['BUDGET_NAME']
    )
    actual = float(resp['Budget']['CalculatedSpend']['ActualSpend']['Amount'])
    limit = float(resp['Budget']['BudgetLimit']['Amount'])

    if actual < limit:
        # Underspend: carry forward to next period
        underspend = limit - actual
        table.update_item(
            Key={'budget': os.environ['BUDGET_NAME']},
            UpdateExpression='ADD rollover :delta',
            ExpressionAttributeValues={':delta': underspend}
        )

    return {'statusCode': 200}
```

Then a second Lambda bumps next month's `BudgetLimit` by the
rollover delta at month start. This is the ONLY way to implement
rollover — there is no native setting.

## STRICT output contract

Every budget action design MUST emit a single block using these literal
labels, in this order. Do NOT substitute markdown headings or camelCase
variants — assertion-based evals and downstream provisioning pipelines
parse the literal labels `BUDGET:`, `VERDICT:`, `CHECKLIST:`, `GAP:`,
`TEMPLATE:`.

```text
BUDGET: <budget-name>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
CHECKLIST:
  [x] Budget type: COST | USAGE | RI_COVERAGE | RI_UTILIZATION | SAVINGS_PLANS_COVERAGE | SAVINGS_PLANS_UTILIZATION
  [x] Monthly amount: <$> <unit> (TimeUnit: MONTHLY | QUARTERLY | ANNUALLY | DAILY)
  [x] Threshold: ACTUAL <percent>% AND/OR FORECASTED <percent>% (PERCENTAGE | ABSOLUTE_VALUE)
  [x] Action: SNS_NOTIFY | SCP_DENY | IAM_RESTRICT | SSM_STOP_EC2 | LAMBDA_CUSTOM
  [x] Cost allocation tags: ACTIVATED | NOT_ACTIVATED | N/A
  [x] Multi-account scope: SINGLE | PAYER_LINKED_ACCOUNT | STACK_SET_PER_OU
  [x] Approval model: AUTOMATIC | MANUAL (start MANUAL; promote to AUTOMATIC after cycle 2)
  [x] Execution role: <arn> (trusts budgets.amazonaws.com, has organizations:AttachPolicy / iam:AttachUserPolicy)
  [x] SCP detach / IAM detach on recovery: WIRED (Lambda scheduled) | NOT WIRED
GAP: <if REVIEW_REQUIRED, the specific gap and remediation>
TEMPLATE: <CLI snippet or CloudFormation; "(held in draft)" if blocked>
```

### FORBIDDEN output patterns — NEVER

1. NEVER emit `VERDICT: AUTOMATION_DEPLOYED` while any CHECKLIST item is
   `[ ]`. Any unmet requirement forces `REVIEW_REQUIRED`.

2. NEVER recommend `Action: SCP_DENY` with `Approval model: AUTOMATIC` in
   a fresh deployment. SCP attach is irreversible until manually detached
   and a false positive locks an entire OU out of resource creation for
   5-15+ minutes. Always start `MANUAL`; promote to `AUTOMATIC` only
   after a false-positive-free cycle.

3. NEVER emit a tag-scoped budget (`CostFilters: Tag`) without verifying
   the tag is `ACTIVATED` in the Billing console. Non-activated tags
   silently match zero spend — the budget never fires and operators
   believe spend is under control.

4. NEVER combine `Access-Control-Allow-Origin: *` style wildcards in
   `CostFilters` with `ThresholdType: ABSOLUTE_VALUE` across multiple
   LinkedAccounts without recalculating per member. An absolute $10K
   threshold across 20 member accounts means $200K total exposure.

5. NEVER claim `Action: SNS_NOTIFY` is enforcement. SNS is reporting,
   not control. If the goal is prevention of further spend, the action
   MUST be `SCP_DENY`, `IAM_RESTRICT`, `SSM_STOP_EC2`, or `LAMBDA_CUSTOM`.

6. NEVER report a budget action as wired without confirming the SNS
   topic policy allows `budgets.amazonaws.com` to publish AND the
   execution role trust policy includes `budgets.amazonaws.com`. Both
   are silent-failure conditions — the budget fires, the action stays
   in `ERROR` state, and no alarm pages.

7. NEVER use `RI_COVERAGE` or `RI_UTILIZATION` budgets for cost control.
   They measure commitment performance, not spend. A 100% RI
   utilization target can be met while overall compute spend triples.

### Worked example — AUTOMATION_DEPLOYED ($10K/month cost budget at 80%, SCP deny at 100%)

```text
BUDGET: monthly-app-cost-budget
VERDICT: AUTOMATION_DEPLOYED
CHECKLIST:
  [x] Budget type: COST (unblended USD spend)
  [x] Monthly amount: 10000 USD (TimeUnit: MONTHLY, resets 1st of month)
  [x] Threshold: FORECASTED 80% (SNS notify — Slack #finops-alerts) AND ACTUAL 100% (SCP deny)
  [x] Action: SNS_NOTIFY at 80% forecast + SCP_DENY at 100% actual
  [x] Cost allocation tags: N/A (no CostFilters — budget covers whole account 111111111111)
  [x] Multi-account scope: SINGLE (account 111111111111, Org member of o-abc123def456)
  [x] Approval model: MANUAL (cycle 1 — notify-only verified; cycle 2 — IAM on CI bot verified; SCP promotes to AUTOMATIC after cycle 3)
  [x] Execution role: arn:aws:iam::111111111111:role/BudgetActionExecutionRole (trusts budgets.amazonaws.com; policy grants organizations:AttachPolicy + organizations:DetachPolicy on ou-abc-123def456)
  [x] SCP detach on recovery: WIRED (EventBridge schedule rule budget-period-reset → Lambda detach-scp-stale at 00:05 UTC on day 1)
GAP: None
TEMPLATE:
  # Budget + 80% forecast SNS notification
  aws budgets create-budget --account-id 111111111111 --budget '{"BudgetName":"monthly-app-cost-budget","BudgetLimit":{"Amount":"10000","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}' \
    --notifications-with-subscribers '[{"Notification":{"NotificationType":"FORECASTED","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"},"Subscribers":[{"SubscriptionType":"SNS","Address":"arn:aws:sns:us-east-1:111111111111:budget-alerts"}]}]'

  # SCP deny at 100% ACTUAL (pre-create the SCP in Organizations first)
  aws organizations create-policy --type SERVICE_CONTROL_POLICY --name budget-breach-deny-new-resources --description "Attached when monthly-app-cost-budget breaches 100% ACTUAL" --content file://scp-deny-new-resources.json

  # Wire the budget action (ApprovalModel: MANUAL — flip to AUTOMATIC after cycle 3)
  aws budgets put-budget-action --account-id 111111111111 --budget-name monthly-app-cost-budget \
    --notification-type ACTUAL --action-type APPLY_SCP_FAMILY \
    --action-threshold '{"ActionThresholdValue":100,"ActionThresholdType":"PERCENTAGE"}' \
    --definition '{"ScpActionDefinition":{"PolicyId":"p-abc123def456","PolicyDocument":"{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Deny\",\"Action\":[\"ec2:RunInstances\",\"ecs:RegisterTaskDefinition\",\"lambda:CreateFunction\"],\"Resource\":\"*\"}]}"}}' \
    --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionExecutionRole --approval-model MANUAL
```

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

### Decision tree — budget action selection

```
Start: budget requirement
├─ Goal = notify only (no enforcement)?
│   └─ Yes → SNS_NOTIFY (create-notification + subscribe)
│            OR APPLY_SSM_ACTION for stop-instances notify-only flows
├─ Goal = enforce on a single account?
│   ├─ Is the account an Org member?
│   │   ├─ Yes → Block new resource creation?
│   │   │       ├─ Yes → APPLY_SCP_FAMILY (target = account itself or leaf OU)
│   │   │       └─ No  → APPLY_IAM_ACTION (target = CI bot user / group, not app roles)
│   │   └─ No (standalone) → APPLY_IAM_ACTION or EventBridge → Lambda
│   └─ Goal = stop running resources? → APPLY_SSM_ACTION (STOP_EC2_INSTANCES, static IDs)
├─ Goal = enforce across OU / fleet?
│   └─ StackSet to OU with APPLY_SCP_FAMILY at innermost leaf OU
└─ Budget type is RI_COVERAGE / RI_UTILIZATION / SAVINGS_PLANS_*?
    └─ Notify-only — NEVER enforcement. RI/SP budgets measure commitment,
       not spend. Wire to SNS for human review.
```

## Anti-Patterns — NEVER do these things

- NEVER wire a budget action with `ApprovalModel: AUTOMATIC` for
  SCP deny without first testing in a non-production OU. A false
  positive locks an entire OU out of resource creation; recovery
  requires manual SCP detach and propagation delay (5-15 minutes).
  Always start with `ApprovalModel: MANUAL` in production.

- NEVER assume `FORECASTED` thresholds are deterministic. AWS
  forecast models are probabilistic (80% confidence). A forecast at
  90% may fire when actual spend is only at 75%. Always pair forecast
  with a higher actual threshold to avoid premature enforcement.

- NEVER scope a budget by `CostFilters: Tag` without verifying the
  tag is activated. Tag-scoped budgets against non-activated tags
  silently match zero spend — the budget never fires and operators
  believe their spend is under control.

- NEVER use a budget as the only enforcement for unexpected spend
  spikes. Budgets evaluate every 8-12 hours and depend on CE data
  that lags 12-24 hours. For real-time spike detection, use Cost
  Anomaly Detection (Step 14) wired to a different SNS topic.

- NEVER forget the SCP detach step on budget recovery. The
  `put-budget-action` API attaches the SCP on breach but does NOT
  detach it when the budget resets next period. Wire a Lambda
  (EventBridge on `ResetPeriod` event) or a monthly scheduled
  Lambda to detach stale SCPs.

- NEVER omit the SNS topic access policy for `budgets.amazonaws.com`.
  A topic created via `sns create-topic` with the default policy
  does NOT allow Budgets to publish. Silent notification failure is
  the most common "budget didn't fire" root cause.

- NEVER attach an IAM policy via budget action to a role used by an
  application. The restricted policy applies immediately on breach
  and breaks the application. Target users (CI bots) or groups, not
  roles in active use.

- NEVER assume a payer-side budget cascades to member accounts.
  Budgets are per-account. For per-member enforcement, use
  `CostFilters: LinkedAccount` from the payer or deploy via
  CloudFormation StackSet to each member.

- NEVER use SSM Action (`APPLY_SSM_ACTION`) for production EC2 stop
  without testing idempotency. The action stops instances on every
  budget evaluation (8-12 hours) while the threshold is breached.
  Instances restarted by an autoscaler will be stopped again. Wire
  a state flag (SSM Parameter) to make the action idempotent.

- NEVER trust budget data for same-day decisions. CE data lags
  12-24 hours. A "real-time" dashboard built on Budgets data
  presents yesterday's spend as today's. Use the Cost and Usage
  Report (CUR) with hourly granularity for near-real-time.

- NEVER create a budget without `describe-budgets` first. Multiple
  teams creating budgets with the same name silently overwrite each
  other — Budgets does NOT enforce uniqueness across
  `Notification`/`Action` configs, only across `BudgetName`.

- NEVER rely on `ThresholdType: ABSOLUTE_VALUE` for multi-account
  budgets without recalculating per member. An absolute $10K
  threshold against 20 member accounts means each member can spend
  $10K (total $200K) — not what most operators expect.

- NEVER wire EventBridge → Lambda budget actions without a DLQ.
  Budget notification events that fail Lambda invocation are
  dropped silently. A missing DLQ produces silent enforcement
  failure.

- NEVER use RI Coverage or RI Utilization budgets for cost control.
  They measure commitment performance, not spend. A 100% RI
  utilization budget can be met while overall compute spend triples
  if the workload grows faster than the RI commitment.

- NEVER enable a budget action in production without verifying the
  execution role trust policy includes `budgets.amazonaws.com`. A
  role that trusts only `ec2.amazonaws.com` or `lambda.amazonaws.com`
  will silently fail to assume — the action stays in `ERROR` state.

- NEVER confuse `APPLY_SCP_FAMILY` (newer API) with the deprecated
  `APPLY_POLICY`. Both attach SCPs, but the API surface differs.
  Stick with `APPLY_SCP_FAMILY` for new code; `APPLY_POLICY` may
  not be supported on newer API versions.

- NEVER forget budget action status checks post-deploy.
  `describe-budget-action-histories` shows the action execution
  history; an action in `EXECUTED` state means it fired. Without
  this check, a misconfigured budget can breach for months with
  no enforcement.

## Pre-flight safety checks (run before applying any budget CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`put-budget-action`, `create-budget`, attaching SCPs,
  modifying the SNS topic policy), emit:
  `CONFIRM: About to <action> for budget <budget> in account
  <account>. This affects <consequence>. Proceed? (yes/no)`

- **Back up the current budget configuration** before modifying:
  `aws budgets describe-budget --account-id <id> --budget-name <name> > /tmp/<name>-backup-$(date +%s).json`

- **Before enabling `ApprovalModel: AUTOMATIC` for SCP**, dry-run
  the SCP in a non-production OU for at least one full budget cycle
  (monthly). Verify the SCP attaches, blocks the expected actions,
  and detaches correctly on budget reset.

- **Before deploying a multi-account budget StackSet**, validate
  the CloudFormation template:
  `aws cloudformation validate-template --template-body file://budget-template.yaml`

- **For cost-allocation-tag-scoped budgets**, verify tag activation
  with `ce get-cost-and-usage --group-by Type=TAG,Key=<key>` BEFORE
  creating the budget. Activated tags return data rows; non-activated
  return only `$NULL`.

## Appendix A — Common budget action types (summary)

The most-used `ActionType` values. The default for any new
enforcement should be SNS notification; escalate to IAM/SCP only
after notification alone has failed to contain spend.

| Pattern | Action type | Reversible | Notes |
|---|---|---|---|
| Notify only | `Notification` (not `put-budget-action`) | Yes | SNS or email |
| Restrict IAM user | `APPLY_IAM_ACTION` | Yes (detach policy) | Per-user enforcement |
| Block new resources | `APPLY_SCP_FAMILY` | Yes (detach SCP) | Org/OU/account scope |
| Stop EC2 | `APPLY_SSM_ACTION` (STOP_EC2_INSTANCES) | Yes (start instances) | Static instance list |
| Custom (Slack, tag, multi-region) | EventBridge → Lambda | Varies | Full Lambda power |

For the full table (input parameters, threshold pairing, safety
profiles, and execution role requirements), see
**references/budget-action-types.md**. Always cross-reference the
action type's parameter contract with your `put-budget-action`
payload.

## Appendix B — Decision tree (which action type)

```
Is the goal enforcement or notification?
├─ Notification only → SNS via create-notification + subscribe
└─ Enforcement → Is the target an Org member account?
                  ├─ Yes → Is the fix blocking new resources?
                  │        ├─ Yes → APPLY_SCP_FAMILY (Step 5)
                  │        └─ No  → APPLY_IAM_ACTION for per-user (Step 6)
                  └─ No (standalone) → APPLY_IAM_ACTION or EventBridge+Lambda (Step 7)

Is the budget type RI/SP coverage or utilization?
└─ Notify-only — no enforcement action. Use SNS for human review.
```

## Recent AWS features (2024-2026)

- **Budgets SSM Action (2024):** Native `APPLY_SSM_ACTION` with
  `STOP_EC2_INSTANCES` subtype. Removes the Lambda middle layer for
  simple stop-instances workflows. Still single-region and static
  instance list.
- **`APPLY_SCP_FAMILY` API rename (2024):** Replaces the deprecated
  `APPLY_POLICY`. Same semantics, cleaner API surface.
- **Budgets CostFilters enhancements (2024-2025):** Support for
  `SAVINGS_PLANS_COVERAGE` and `SAVINGS_PLANS_UTILIZATION` budget
  types — modern alternative to RI-based commitment tracking.
- **Cost Anomaly Detection weekly anomaly subscriptions (2025):**
  Complements daily subscriptions for less-noisy trend detection.
  Useful when pairing with Budgets for layered monitoring.
- **Budgets EventBridge detail enrichment (2025):** Budget
  notification events now include `ActualSpend`,
  `ForecastedSpend`, and `BudgetLimit` in the `detail` block —
  richer Lambda handlers without `describe-budget` round-trip.

## Expert heuristic: budget enforcement blast radius

Budget enforcement is the highest-leverage FinOps control but also
the highest-risk. A misconfigured `APPLY_SCP_FAMILY` action at 90%
threshold can lock an entire OU out of resource creation for 24+
hours before operators notice.

**The rule (non-negotiable):**

> ALWAYS start budget actions in `ApprovalModel: MANUAL` mode. Switch
> to `AUTOMATIC` only after at least one full budget cycle
> (monthly) of false-positive-free operation in production. Always
> scope SCPs to the smallest OU that contains the offending spend.

**Why this rule exists:** Budget thresholds fire on stale data (12-24
hour lag). A forecast spike that triggers a 90% SCP attach may
reflect spend from yesterday that has already self-corrected. The
SCP remains attached until manually detached. Recovery time is 5-15
minutes (Org propagation) plus detection time.

**Concrete scoping techniques:**

| Technique | Mechanism | Blast-radius limit |
|---|---|---|
| `ApprovalModel: MANUAL` | Requires IAM user to approve each fire | Human gate per execution |
| SCP at innermost OU | Attach to leaf OU, not root | Affects smallest possible account set |
| Tag-scoped IAM policy | Attach only to `tag:env=dev` users | Production users unaffected |
| Forecast-only threshold | No enforcement action, just notify | Zero enforcement risk; information only |
| Stacked thresholds (80% notify, 100% IAM, 110% SCP) | Graduated response | Hard enforcement only on confirmed breach |

**Pre-production validation protocol (3-cycle rule):**

1. **Cycle 1 — NOTIFY-ONLY:** Deploy the budget with SNS
   notifications at 80/90/100%. Monitor for 1 full month. Verify
   forecast accuracy and actual-spend correlation.
2. **Cycle 2 — AUTOMATIC IAM in non-prod:** Add
   `APPLY_IAM_ACTION` against a CI bot user. Plant a test workload
   that exceeds the budget. Verify the policy attaches, blocks the
   user, and that production is unaffected.
3. **Cycle 3 — AUTOMATIC SCP in prod:** Promote to production with
   `APPLY_SCP_FAMILY` at 110% (above forecast band). Monitor for
   one month of false-positive-free operation. If zero false
   positives, lower threshold to 100%. If any false positive,
   refine budget scope and re-run Cycle 2.

**CloudFormation scoping pattern (recommended for fleet rollout):**

```yaml
# Budget with manual approval, promotable to automatic
Resources:
  CostBudget:
    Type: AWS::Budgets::Budget
    Properties:
      Budget:
        BudgetName: prod-cost-budget
        BudgetLimit:
          Amount: 50000
          Unit: USD
        TimeUnit: MONTHLY
        BudgetType: COST

  BudgetScpAction:
    Type: AWS::Budgets::BudgetsAction
    Properties:
      BudgetName: !Ref CostBudget
      NotificationType: ACTUAL
      ActionType: APPLY_SCP_FAMILY
      ActionThreshold:
        ActionThresholdValue: 100
        ActionThresholdType: PERCENTAGE
      Definition:
        ScpActionDefinition:
          PolicyId: !ImportValue budget-breach-scp-id
      ExecutionRoleArn: !GetAtt BudgetActionRole.Arn
      ApprovalModel: MANUAL  # Flip to AUTOMATIC only after Cycle 2
```

**Detection of blast-radius breach post-deploy:** CloudWatch alarm on
`AWS/Budgets > BudgetedAndActualCost` variance > N% in 24 hours
(suggests stale data firing false positives). Also alarm on
`AWS/Organizations > PolicyAttachmentsChangedByBudgets` count > N
in 24 hours (suggests budget firing repeatedly). Both alarms should
page the on-call FinOps team and trigger an EventBridge rule that
flips `ApprovalModel` to `MANUAL` on the offending action via
`update-budget-action`.

**Surface in the output:** for any recommended budget action,
include `BLAST_RADIUS: <scope>` (e.g., `OU-wide`,
`tag-scoped:env=prod`, `single-account`, `single-user`) and
`VALIDATION_STATUS: <notify-only | iam-non-prod | scp-prod-manual
| scp-prod-automatic>`. If `VALIDATION_STATUS` is not
`scp-prod-automatic`, do NOT mark the SCP recommendation as
deployable.

## Domain

AWS CloudOps / FinOps Automation — Budget-driven enforcement.

## AWS documentation

- **AWS Budgets** — https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- **Budget Actions** — https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html
- **Cost Anomaly Detection** — https://docs.aws.amazon.com/cost-management/latest/userguide/manage-anomalies.html
- **Organizations SCPs** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- **Cost Allocation Tags** — https://docs.aws.amazon.com/cost-management/latest/userguide/alloc-tags.html
