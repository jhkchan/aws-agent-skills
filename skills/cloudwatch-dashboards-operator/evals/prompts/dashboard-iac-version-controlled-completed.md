# Eval prompt: dashboard-iac-version-controlled-completed

Plan the following CloudWatch dashboard update via version-controlled
IaC and emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: update-dashboard
Dashboard: prod-rds-overview (existing)
Change: 8 widgets to 10 widgets (additive)
New widgets: replica-lag-metric-math, alarm-secondary
Source: dashboards/prod-rds-overview.json (Git-tracked)

```json
{
  "CurrentDashboard": {
    "DashboardName": "prod-rds-overview",
    "WidgetCount": 8,
    "BodySize": "14 KB",
    "CapturedTo": "/tmp/prod-rds-overview-pre-1234567890.json"
  },
  "ProposedDashboard": {
    "WidgetCount": 10,
    "ValidJson": true,
    "Diff": "+2 new widgets (replica-lag-metric-math, alarm-secondary)",
    "ExistingWidgetsRemoved": false
  },
  "Source": "dashboards/prod-rds-overview.json"
}
```
