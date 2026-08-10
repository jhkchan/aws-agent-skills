# Baseline (no-skill) response: deploy-cross-account-dashboard-prereqs-missing

This file captures what a generic assistant produces WITHOUT the
cloudwatch-dashboard-deployer skill loaded.

---

To create a cross-account dashboard, you need to set up the
CloudWatch-CrossAccountSharingRole in each source account. Then use:

```bash
aws cloudwatch put-dashboard \
  --dashboard-name cross-account-ec2-ops \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "x": 0, "y": 0, "width": 12, "height": 6,
        "properties": {
          "metrics": [["AWS/EC2", "CPUUtilization", "InstanceId", "i-0123456789abcdef0"]],
          "title": "Dev Account CPU"
        }
      }
    ]
  }'
```

Make sure you configure the cross-account sharing roles first.
