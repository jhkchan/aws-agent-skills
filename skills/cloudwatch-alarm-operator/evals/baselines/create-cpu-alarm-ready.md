# Baseline (no-skill) response: create-cpu-alarm-ready

This file captures what a generic assistant produces WITHOUT the
cloudwatch-alarm-operator skill loaded.

---

To create a CPU alarm for your EC2 instance, use:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name ec2-cpu-high-prod-web-1 \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-0123456789abcdef0 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:111111111111:on-call-critical
```

You should also set OK actions if you want to be notified when CPU
returns to normal.
