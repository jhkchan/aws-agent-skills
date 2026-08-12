# Eval prompt: cross-account-dashboard-oam-review

Plan the following cross-account CloudWatch dashboard creation using
OAM shared observability and emit the standard VERDICT block
(OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: enable-cross-account
Dashboard: cross-account-rds-overview
Monitoring account: 111111111111
Source accounts: 222222222222, 333333333333

```json
{
  "OamSinks": [
    {
      "SinkName": "org-monitoring-sink",
      "Account": "111111111111",
      "Status": "ACTIVE"
    }
  ],
  "OamLinks": [
    {
      "SourceAccount": "222222222222",
      "LinkStatus": "LINKED",
      "MetricLink": true
    },
    {
      "SourceAccount": "333333333333",
      "LinkStatus": "LINKED",
      "MetricLink": true
    }
  ],
  "DashboardPlan": {
    "Widget1": "RDS CPU across all linked accounts (@Account variable)",
    "Widget2": "Metrics Insights top 10 RDS instances by CPU across all accounts",
    "Widget3": "Alarm widget for cross-account RDS alarms"
  }
}
```
