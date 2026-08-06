# Eval prompt: no-budgets-account

Audit the following AWS Budgets account configuration for cost-overrun blind
spots. Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit reference: no-budgets-account
Account id: 111111111111
Account context: newly created production account, no prior budget history.

Budget inventory (aws budgets describe-budgets):

```json
{"Budgets": []}
```

Notifications for each budget: (none — no budgets exist)
SNS topic policies: (none — no budget subscribers exist)
Calculated spend: (no budgets to calculate against)
