# Eval prompt: new-account-no-zero-spend

Audit the following AWS Budgets account configuration for cost-overrun blind
spots. Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit reference: new-account-no-zero-spend
Account id: 666666666666
Account context: new sandbox account, provisioned last week, expected minimal
spend.

Budget inventory (aws budgets describe-budgets):

```json
{
  "Budgets": [
    {
      "BudgetName": "monthly-total",
      "BudgetType": "COST",
      "TimeUnit": "MONTHLY",
      "BudgetLimit": {"Amount": "500.0", "Unit": "USD"},
      "CostTypes": {"IncludeTax": true, "UseAmortized": false, "IncludeDiscount": true},
      "CalculatedSpend": {
        "ActualSpend": {"Amount": "45.0", "Unit": "USD"},
        "ForecastedSpend": {"Amount": "180.0", "Unit": "USD"}
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
      "Notification": {"NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN", "Threshold": 50.0, "ThresholdType": "PERCENTAGE"},
      "Subscribers": [{"SubscriptionType": "SNS", "Address": "arn:aws:sns:us-east-1:666666666666:budget-alerts"}]
    },
    {
      "NotificationType": "FORECASTED",
      "Notification": {"NotificationType": "FORECASTED", "ComparisonOperator": "GREATER_THAN", "Threshold": 80.0, "ThresholdType": "PERCENTAGE"},
      "Subscribers": [{"SubscriptionType": "SNS", "Address": "arn:aws:sns:us-east-1:666666666666:budget-alerts"}]
    },
    {
      "NotificationType": "ACTUAL",
      "Notification": {"NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN", "Threshold": 100.0, "ThresholdType": "PERCENTAGE"},
      "Subscribers": [{"SubscriptionType": "SNS", "Address": "arn:aws:sns:us-east-1:666666666666:budget-alerts"}]
    }
  ]
}
```

SNS topic policy for arn:aws:sns:us-east-1:666666666666:budget-alerts:

```json
{
  "Version": "2008-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "budgets.amazonaws.com"},
      "Action": "SNS:Publish",
      "Resource": "arn:aws:sns:us-east-1:666666666666:budget-alerts"
    }
  ]
}
```

Note: no zero-spend or low-spend guardrail budget exists in the inventory.
