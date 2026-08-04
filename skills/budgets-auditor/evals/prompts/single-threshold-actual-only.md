# Eval prompt: single-threshold-actual-only

Audit the following AWS Budgets account configuration for cost-overrun blind
spots. Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit reference: single-threshold-actual-only
Account id: 444444444444
Account context: production account, budget alerts deliver but always arrive
after the spend is already incurred.

Budget inventory (aws budgets describe-budgets):

```json
{
  "Budgets": [
    {
      "BudgetName": "monthly-total",
      "BudgetType": "COST",
      "TimeUnit": "MONTHLY",
      "BudgetLimit": {"Amount": "8000.0", "Unit": "USD"},
      "CostTypes": {"IncludeTax": true, "UseAmortized": false, "IncludeDiscount": true},
      "CalculatedSpend": {
        "ActualSpend": {"Amount": "5400.0", "Unit": "USD"},
        "ForecastedSpend": {"Amount": "7600.0", "Unit": "USD"}
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
        {
          "SubscriptionType": "SNS",
          "Address": "arn:aws:sns:us-east-1:444444444444:budget-alerts"
        }
      ]
    }
  ]
}
```

SNS topic policy for arn:aws:sns:us-east-1:444444444444:budget-alerts:

```json
{
  "Version": "2008-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "budgets.amazonaws.com"},
      "Action": "SNS:Publish",
      "Resource": "arn:aws:sns:us-east-1:444444444444:budget-alerts"
    }
  ]
}
```

Note: SNS policy is correctly configured for budgets delivery.
