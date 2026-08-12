# Baseline (no-skill) response: dashboard-iac-version-controlled-completed

This file captures what a generic assistant produces WITHOUT the
cloudwatch-dashboards-operator skill loaded.

---

To update your dashboard, run put-dashboard with the updated JSON file:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name prod-rds-overview \
  --dashboard-body file://dashboards/prod-rds-overview.json
```

This will replace the existing dashboard with the new version. Make
sure your JSON file is valid before deploying. You can verify the
update with get-dashboard afterwards.
