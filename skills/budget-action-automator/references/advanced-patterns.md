# Advanced Patterns (load on demand) — Budget Action Automator

Expert-knowledge deep dives, custom-action patterns, edge cases, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Step 0: Expert knowledge — non-obvious Budgets behaviors (moved from SKILL.md)

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

## Step 7 — EventBridge → Lambda for custom action (moved from SKILL.md)

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

## Step 8 — Stop non-prod EC2 on budget breach (moved from SKILL.md)

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

## Step 9 — Tag untagged resources via budget action (moved from SKILL.md)

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

## Step 10 — Slack notification via Lambda (moved from SKILL.md)

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

## Step 14 — Budget vs Cost Anomaly Detection (moved from SKILL.md)

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

## Step 15 — Budget rollover / reset semantics (moved from SKILL.md)

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

## Recent AWS features (2024-2026) (moved from SKILL.md)

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

## Expert heuristic: budget enforcement blast radius (moved from SKILL.md)

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
