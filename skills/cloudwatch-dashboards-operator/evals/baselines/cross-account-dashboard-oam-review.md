# Baseline (no-skill) response: cross-account-dashboard-oam-review

This file captures what a generic assistant produces WITHOUT the
cloudwatch-dashboards-operator skill loaded.

---

To create a cross-account dashboard, use the @Account dimension in your
widgets after setting up OAM:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name cross-account-rds-overview \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "properties": {
          "metrics": [["AWS/RDS", "CPUUtilization"]],
          "view": "timeSeries",
          "title": "RDS CPU - All Accounts"
        }
      }
    ]
  }'
```

Make sure your OAM sink and links are set up. You can filter by account
in the console.
