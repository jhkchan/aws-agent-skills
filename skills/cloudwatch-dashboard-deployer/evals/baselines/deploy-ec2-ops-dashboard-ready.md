# Baseline (no-skill) response: deploy-ec2-ops-dashboard-ready

This file captures what a generic assistant produces WITHOUT the
cloudwatch-dashboard-deployer skill loaded.

---

To create a CloudWatch dashboard for your EC2 instance, use:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name prod-ec2-ops \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0, "y": 0, "width": 12, "height": 6,
        "properties": {
          "metrics": [["AWS/EC2", "CPUUtilization", "InstanceId", "i-0123456789abcdef0"]],
          "period": 300,
          "stat": "Average",
          "title": "CPU Utilization"
        }
      }
    ]
  }'
```

You can add more widgets for memory and network metrics.
