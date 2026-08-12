# Multi-Account Budget Patterns Reference

Supplementary reference for the Budget Action Automator skill. Use
when designing budget enforcement across an AWS Organization,
picking between payer-scoped vs per-member budgets, or building
CloudFormation StackSet rollouts.

## Architecture patterns

### Pattern 1: Payer-scoped budget with `LinkedAccount` filter

The budget lives in the payer account; one budget per member
account via `CostFilters`.

```bash
aws budgets create-budget \
  --account-id <payer-id> \
  --budget '{
    "BudgetName": "team-alpha-prod-budget",
    "BudgetLimit": {"Amount": "50000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {"LinkedAccount": ["111111111111"]}
  }'
```

**Pros:** central visibility; SCP attach from payer.
**Cons:** one budget per member (no template); SCP target must be
  the member account, not the payer.

### Pattern 2: CloudFormation StackSet per OU

Deploy the same budget to every member account in an OU via
StackSet with `SERVICE_MANAGED` permission model.

```bash
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

**Pros:** fleet consistency; new accounts auto-included.
**Cons:** budgets live in each member (no central visibility
  without CUR aggregation).

### Pattern 3: Tag-based cross-account budget in payer

One budget covering all resources across all accounts with a given
tag value.

```bash
aws budgets create-budget \
  --account-id <payer-id> \
  --budget '{
    "BudgetName": "all-prod-spend",
    "BudgetLimit": {"Amount": "500000", "Unit": "USD"},
    "TimeUnit": "MONTHLY",
    "BudgetType": "COST",
    "CostFilters": {"Tag": ["env:prod"]}
  }'
```

**Pros:** single budget; matches cross-account spend.
**Cons:** requires `env` tag activated in payer Billing console
  (24-hour propagation). SCP cannot target a tag scope — it must
  target an account or OU, so SCP enforcement is awkward.

### Pattern 4: SCP at the OU level on breach

For fleet-wide hard enforcement, attach an SCP at the OU when the
aggregate budget breaches. Use the payer-scoped budget + Lambda
(EventBridge-driven) to attach the SCP.

```python
import boto3
orgs = boto3.client('organizations')

def lambda_handler(event, context):
    budget_name = event['detail']['BudgetName']
    if budget_name == 'all-prod-spend':
        orgs.attach_policy(
            PolicyId='p-breach-deny-new-ec2',
            TargetId='ou-abc-123def456'  # the prod OU
        )
    return {'statusCode': 200}
```

**Pros:** one SCP, fleet effect.
**Cons:** SCP affects ALL accounts in the OU including those not
  contributing to the breach. Use with care.

## CloudFormation template (StackSet-ready)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: Per-account monthly cost budget with SNS notification

Parameters:
  BudgetLimit:
    Type: Number
    Description: Monthly budget limit in USD
  NotificationTopicArn:
    Type: String
    Description: SNS topic ARN for budget alerts

Resources:
  MonthlyCostBudget:
    Type: AWS::Budgets::Budget
    Properties:
      Budget:
        BudgetName: !Sub 'monthly-cost-budget-${AWS::AccountId}'
        BudgetLimit:
          Amount: !Ref BudgetLimit
          Unit: USD
        TimeUnit: MONTHLY
        BudgetType: COST
      NotificationsWithSubscribers:
        - Notification:
            NotificationType: FORECASTED
            ComparisonOperator: GREATER_THAN
            Threshold: 80
            ThresholdType: PERCENTAGE
          Subscribers:
            - SubscriptionType: SNS
              Address: !Ref NotificationTopicArn
        - Notification:
            NotificationType: ACTUAL
            ComparisonOperator: GREATER_THAN
            Threshold: 100
            ThresholdType: PERCENTAGE
          Subscribers:
            - SubscriptionType: SNS
              Address: !Ref NotificationTopicArn
```

## Multi-account gotchas

- **Budgets are per-account by default.** A payer-side budget does
  NOT cascade to member accounts. Each member needs its own budget
  OR the payer budget uses `CostFilters: LinkedAccount`.
- **SCP enforcement requires Organization membership.** A standalone
  account cannot use `APPLY_SCP_FAMILY`. Verify the target account
  is an Org member before wiring SCP actions.
- **Delegated admin for Cost Explorer is NOT delegated admin for
  Budgets.** Budgets do not have a delegated-admin model. All
  budgets must be created in the account that owns the spend (payer
  for linked-account-filtered budgets, member for per-account
  budgets).
- **StackSet deployment of budget actions requires
  `CAPABILITY_IAM`** because the budget action execution role is
  an IAM resource. Add `--capabilities CAPABILITY_IAM` to
  `create-stack-set`.
- **Cost allocation tags must be activated in the PAYER Billing
  console** for tag-scoped budgets to work cross-account. Member
  account tag activation does not affect payer-side budgets.

## Selecting a pattern

| Requirement | Pattern | Notes |
|---|---|---|
| Central visibility + per-member enforcement | Pattern 1 (payer-scoped) | One budget per LinkedAccount |
| Fleet consistency + auto-onboard new accounts | Pattern 2 (StackSet) | Member-side budgets |
| Cross-account tag-based cost tracking | Pattern 3 (tag in payer) | Requires tag activation |
| Fleet-wide hard lock on breach | Pattern 4 (SCP at OU) | Use with care; affects all members |
