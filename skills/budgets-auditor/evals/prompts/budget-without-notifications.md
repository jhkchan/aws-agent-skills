# Eval prompt: budget-without-notifications

Audit the following AWS Budgets account configuration for cost-overrun blind
spots. Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit reference: budget-without-notifications
Account id: 222222222222
Account context: established production account.

Budget inventory (aws budgets describe-budgets):

```json
{
  "Budgets": [
    {
      "BudgetName": "monthly-total",
      "BudgetType": "COST",
      "TimeUnit": "MONTHLY",
      "BudgetLimit": {"Amount": "10000.0", "Unit": "USD"},
      "CostTypes": {"IncludeTax": true, "UseAmortized": false, "IncludeDiscount": true},
      "CalculatedSpend": {
        "ActualSpend": {"Amount": "4200.0", "Unit": "USD"},
        "ForecastedSpend": {"Amount": "9100.0", "Unit": "USD"}
      }
    }
  ]
}
```

Notifications for "monthly-total" (aws budgets describe-notifications-for-budget):

```json
{"Notifications": []}
```

SNS topic policies: (no SNS subscribers configured)
