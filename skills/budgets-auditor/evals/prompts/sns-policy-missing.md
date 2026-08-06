# Eval prompt: sns-policy-missing

Audit the following AWS Budgets account configuration for cost-overrun blind
spots. Emit the standard VERDICT block (ACCOUNT, VERDICT, REASON, FINDINGS,
REMEDIATION).

Audit reference: sns-policy-missing
Account id: 333333333333
Account context: production account with a budget configured but alerts never
seem to arrive.

Budget inventory (aws budgets describe-budgets):

```json
{
  "Budgets": [
    {
      "BudgetName": "monthly-total",
      "BudgetType": "COST",
      "TimeUnit": "MONTHLY",
      "BudgetLimit": {"Amount": "5000.0", "Unit": "USD"},
      "CostTypes": {"IncludeTax": true, "UseAmortized": false, "IncludeDiscount": true},
      "CalculatedSpend": {
        "ActualSpend": {"Amount": "3100.0", "Unit": "USD"},
        "ForecastedSpend": {"Amount": "4700.0", "Unit": "USD"}
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
          "Address": "arn:aws:sns:us-east-1:333333333333:budget-alerts"
        }
      ]
    }
  ]
}
```

SNS topic policy for arn:aws:sns:us-east-1:333333333333:budget-alerts:

```json
{
  "Version": "2008-10-17",
  "Id": "__default_policy_ID",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::333333333333:root"},
      "Action": "SNS:Publish",
      "Resource": "arn:aws:sns:us-east-1:333333333333:budget-alerts"
    }
  ]
}
```

Note: the policy grants the account root publish, but does NOT grant the
budgets.amazonaws.com service principal publish.
