# Baseline (no-skill) response: create-rds-dashboard-completed

This file captures what a generic assistant produces WITHOUT the
cloudwatch-dashboards-operator skill loaded.

---

To create an RDS dashboard, use the put-dashboard API with a JSON body:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name prod-rds-overview \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0, "y": 0, "width": 12, "height": 6,
        "properties": {
          "metrics": [["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "prod-orders-db"]],
          "period": 300,
          "stat": "Average",
          "region": "us-east-1",
          "title": "RDS CPU Utilization"
        }
      }
    ]
  }'
```

Add more widgets for memory, connections, and storage as needed. You
can verify it was created with `get-dashboard`.
