# Eval prompt: scp-deny-hard-enforcement

Design a Budgets automation workflow for the following cost budget
with SCP deny hard enforcement. Emit the standard BUDGET ACTION
block (TYPE, LIMIT, TIME_UNIT, THRESHOLD, NOTIFICATION, RESPONSE,
MULTI_ACCOUNT, COST_ALLOCATION_TAGS, VERDICT, TEMPLATE).

Design reference: scp-deny-hard-enforcement
Account: 111111111111 (member of org o-abc123def)
Region: us-east-1

Budget type: COST
Limit: $50,000 USD / MONTHLY
Threshold: ACTUAL 100% -> APPLY_SCP_FAMILY deny new ec2:RunInstances
Org target: account 111111111111
Existing SCP ID to attach: p-breach000123 (already created)
Execution role ARN: arn:aws:iam::111111111111:role/BudgetActionExecutionRole
Approval model: AUTOMATIC (validated in non-prod for 1 cycle).
