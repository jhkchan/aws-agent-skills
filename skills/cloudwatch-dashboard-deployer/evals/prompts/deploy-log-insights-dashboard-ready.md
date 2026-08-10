# Eval prompt: deploy-log-insights-dashboard-ready

Plan the following CloudWatch dashboard creation and emit the standard
VERDICT block (DASHBOARD, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, WIDGETS, SHARING, NOTES).

Operation: create
Dashboard name: prod-lambda-errors
Region: us-east-1
Account: 111111111111
Widgets:
  - type: log
    title: Lambda Errors (5-min buckets)
    query: >
      SOURCE '/aws/lambda/prod-checkout'
      | fields @timestamp, @message
      | filter @message like /ERROR/
      | stats count() by bin(5m)
      | sort @timestamp desc
      | limit 100
    position: x=0, y=0, w=24, h=6
  - type: log
    title: Top Error Messages
    query: >
      SOURCE '/aws/lambda/prod-checkout'
      | filter @message like /ERROR/
      | stats count() as errorCount by @message
      | sort errorCount desc
      | limit 10
    position: x=0, y=6, w=24, h=6

```json
{
  "LogGroupChecks": {
    "logs.describe-log-groups./aws/lambda/prod-checkout": {
      "status": "OK",
      "storedBytes": 524288000,
      "eventsReceivedLastHour": 1247
    }
  },
  "ExistingDashboard": null
}
```
