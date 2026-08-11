# Budget Types, Actions, and CostFilters — AWS Budget Deployer

Deep reference covering budget type semantics, action-type constraints,
CostFilters dimension values, and cross-principal SNS wiring. Loaded
on-demand when the skill needs the full table rather than the summary
in the SKILL.md.

## BudgetType matrix

| BudgetType | BudgetLimit.Unit | NotificationType supported | ComparisonOperator | Budget actions supported? | Notes |
|---|---|---|---|---|---|
| `COST` | `USD` | `ACTUAL`, `FORECAST` | `GREATER_THAN` | YES (all action types) | Standard spend budget; alerts fire when spend crosses threshold |
| `RI_UTILIZATION` | `PERCENTAGE` | `ACTUAL` only | `LESS_THAN` | NO | Alerts when RI utilization drops below target |
| `RI_COVERAGE` | `PERCENTAGE` | `ACTUAL` only | `LESS_THAN` | NO | Alerts when % of compute spend covered by RI drops below target |
| `SP_UTILIZATION` | `PERCENTAGE` | `ACTUAL` only | `LESS_THAN` | NO | Savings Plan commitment utilization (2024-2025 GA) |
| `SP_COVERAGE` | `PERCENTAGE` | `ACTUAL` only | `LESS_THAN` | NO | % of compute spend covered by Savings Plan (2024-2025 GA) |
| (anomaly) | N/A | N/A | N/A | N/A | Not a BudgetType — uses Cost Explorer API (`create-anomaly-monitor` + `create-anomaly-subscription`) |

**Common mistake:** setting `ComparisonOperator=GREATER_THAN` on a usage
budget. Utilization/coverage alerts should fire when the actual DROPS
BELOW the target (under-utilization is the bad state). Always use
`LESS_THAN` for `RI_*` and `SP_*` budgets.

## Budget action types

| Action type | Definition field | Sub-type | Effect | Approval model |
|---|---|---|---|---|
| `APPLY_IAM_POLICY` | `IamActionDefinition.PolicyArn` + one of `Roles` / `Users` / `Groups` | N/A | Attaches the named IAM policy to the listed principals | `AUTOMATIC` or `MANUAL` |
| `REMOVE_IAM_POLICY` | same as above | N/A | Detaches the named IAM policy from the listed principals | `AUTOMATIC` or `MANUAL` |
| `RUN_SSM_DOCUMENTS` | `SsmActionDefinition` (ActionSubType, Region, InstanceIds) | `STOP_EC2_INSTANCES` | Stops the listed EC2 instances via SSM Automation | `AUTOMATIC` or `MANUAL` |
| `RUN_SSM_DOCUMENTS` | same | `STOP_RDS_INSTANCE` | Stops the listed RDS instances (2024 GA — useful for non-prod databases overnight) | `AUTOMATIC` or `MANUAL` |
| (SNS notification — not an "action") | `create-notification` with SNS subscriber | N/A | Publishes a message to the SNS topic | N/A |

**ExecutionRoleArn permission matrix:**

| Action type | Required IAM permissions on the ExecutionRole |
|---|---|
| `APPLY_IAM_POLICY` | `iam:AttachUserPolicy`, `iam:AttachRolePolicy`, `iam:AttachGroupPolicy`, `iam:ListAttached*Policies` |
| `REMOVE_IAM_POLICY` | `iam:DetachUserPolicy`, `iam:DetachRolePolicy`, `iam:DetachGroupPolicy`, `iam:ListAttached*Policies` |
| `RUN_SSM_DOCUMENTS` | `ssm:StartAutomationExecution`, `ec2:DescribeInstances` (for EC2 stop), `rds:DescribeDBInstances` (for RDS stop) |

The ExecutionRoleArn MUST have a trust policy allowing
`Principal: Service: budgets.amazonaws.com` to `sts:AssumeRole`. A role
that trusts only an IAM user or another role will fail at action
execution time, not at create time.

## Cross-account budget actions

For a budget on a payer account that targets resources in a linked
account, the `ExecutionRoleArn` MUST exist in the linked account, not
the payer. The role trust policy still names `budgets.amazonaws.com`.

Typical pattern:
1. Payer account provisions the budget (COST type, CostFilters on
   `LinkedAccount` for the target linked account).
2. Linked account provisions the ExecutionRoleArn with the appropriate
   permissions and trust on `budgets.amazonaws.com`.
3. Payer account calls `create-budget-action` with the linked-account
   role ARN.

## CostFilters reference

| Dimension | Key in CostFilters | Value format | Notes |
|---|---|---|---|
| Linked account | `LinkedAccount` | 12-digit account ID | Payer only |
| Service | `Service` | Cost Explorer service name | Verify with `aws ce get-dimension-values --dimension SERVICE` |
| Tag | `TagKeyValue` | `key$value` | Tag must be activated in Billing → Cost Allocation Tags; ~24h propagation |
| Region | `Region` | Region display name (`US East (N. Virginia)`) | Not the CLI region name (`us-east-1`) |
| AZ | `AZ` | `us-east-1a` | Rarely useful for budgets |
| PurchaseType | `PurchaseType` | `Reserved Instances`, `On Demand Instances`, `Savings Plans` | For RI/SP-specific budgets |
| UsageTypeGroup | `UsageTypeGroup` | `EC2: Running Hours`, `S3: Storage` | Coarser grouping |

**Verify dimension values before deploying:**

```bash
aws ce get-dimension-values \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --dimension SERVICE \
  --query 'DimensionValues[].Value' --output table
```

## SNS topic policy — the two principals

Budgets and Cost Anomaly Detection publish as **different service
principals**. A topic policy that allows only one will silently drop
notifications from the other.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": [
        "budgets.amazonaws.com",
        "ce.amazonaws.com"
      ]
    },
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:us-east-1:<account-id>:<topic-name>"
  }]
}
```

**If the topic uses SSE-KMS with a customer CMK**, the KMS key policy
must additionally grant:

```json
{
  "Effect": "Allow",
  "Principal": {
    "Service": ["budgets.amazonaws.com", "ce.amazonaws.com"]
  },
  "Action": ["kms:GenerateDataKey*", "kms:Decrypt"],
  "Resource": "*"
}
```

AWS-managed `alias/aws/sns` does not need this — it works out-of-the-box.

## Anomaly monitor types

| Monitor type | Use case | Provisioning |
|---|---|---|
| `DIMENSIONAL` (SERVICE) | Per-service anomaly detection — cleanest signal | `create-anomaly-monitor` with `MonitorDimension=SERVICE` |
| `DIMENSIONAL` (LINKED_ACCOUNT) | Per-linked-account anomaly (payer only) | `create-anomaly-monitor` with `MonitorDimension=LINKED_ACCOUNT` |
| `CUSTOM` | User-defined filter (e.g., specific tags, services) | `create-anomaly-monitor` with `MonitorSpecification` JSON |
| Default (account-wide) | Auto-created when Cost Explorer enabled | ARN: `arn:aws:ce::<account-id>:anomaly-monitor/default` |

The ML model needs ~30 days of Cost Explorer history before predictions
are reliable. Use `put-feedback --is-anomaly NO` for confirmed false
positives — console "dismiss" does not train the model.

## CostTypes field reference

| Field | Default | When to change |
|---|---|---|
| `IncludeTax` | `true` | Set `false` to alert on pre-tax spend only (rare) |
| `IncludeSubscription` | `true` | Set `false` to exclude AWS Support, Marketplace subs |
| `UseBlended` | `false` | Set `true` for blended cost across linked accounts (usually NOT what you want — masks overages) |
| `IncludeRefund` | `false` | Set `true` to net refunds into the budget |
| `IncludeCredit` | `true` | Credits reduce apparent spend; set `false` for gross spend |
| `IncludeUpfront` | `true` | RI/SP upfront payments |
| `IncludeRecurring` | `true` | RI/SP recurring fees |
| `IncludeOtherSubscription` | `true` | Other subscription charges |
| `IncludeSupport` | `true` | AWS Support charges |
| `IncludeDiscount` | `true` | EDP / discount application |
| `UseAmortized` | `false` | Set `true` for amortized RI/SP cost analysis (vs cash budgeting) |

**Production default:** all `Include*` true, `UseBlended=false`,
`UseAmortized=false`. This matches the invoice total — operators can
reconcile alert thresholds against the monthly bill.
