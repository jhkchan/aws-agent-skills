# Baseline (no-skill) response: metrics-insights-dashboard-completed

This file captures what a generic assistant produces WITHOUT the
cloudwatch-dashboards-operator skill loaded.

---

To create a dashboard with Metrics Insights, use the metric widget type
with a query property:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name top10-ec2-by-cpu \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0, "y": 0, "width": 24, "height": 6,
        "properties": {
          "query": "SELECT avg(CPUUtilization) FROM AWS/EC2 WHERE AutoScalingGroupName LIKE '\''prod-%'\'' GROUP BY InstanceId ORDER BY avg() DESC LIMIT 10",
          "title": "Top 10 EC2 by CPU",
          "view": "table"
        }
      }
    ]
  }'
```

This will show the top 10 instances by average CPU utilization.
