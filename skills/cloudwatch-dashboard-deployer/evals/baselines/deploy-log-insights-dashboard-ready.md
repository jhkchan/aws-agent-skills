# Baseline (no-skill) response: deploy-log-insights-dashboard-ready

This file captures what a generic assistant produces WITHOUT the
cloudwatch-dashboard-deployer skill loaded.

---

To create a dashboard with log insights widgets, you can use the AWS
CLI or the CloudWatch console. Here's an example:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name prod-lambda-errors \
  --dashboard-body '{
    "widgets": [
      {
        "type": "log",
        "x": 0, "y": 0, "width": 24, "height": 6,
        "properties": {
          "query": "fields @timestamp, @message | filter @message like /ERROR/ | stats count() by bin(5m)",
          "title": "Lambda Errors"
        }
      }
    ]
  }'
```

Make sure your log group exists before creating the dashboard.
