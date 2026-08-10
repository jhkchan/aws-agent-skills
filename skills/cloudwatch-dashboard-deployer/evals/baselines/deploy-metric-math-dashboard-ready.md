# Baseline (no-skill) response: deploy-metric-math-dashboard-ready

This file captures what a generic assistant produces WITHOUT the
cloudwatch-dashboard-deployer skill loaded.

---

To create a dashboard with metric math for error rate, use:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name prod-alb-error-rate \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0, "y": 0, "width": 24, "height": 6,
        "properties": {
          "metrics": [
            ["AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count", "LoadBalancer", "app/prod-alb/1234567890"],
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/prod-alb/1234567890"]
          ],
          "period": 60,
          "stat": "Sum",
          "title": "ALB Error Rate"
        }
      }
    ]
  }'
```

You would need to configure metric math expressions in the console.
