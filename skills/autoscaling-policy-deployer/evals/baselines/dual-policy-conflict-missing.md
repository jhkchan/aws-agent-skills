# Baseline (no-skill) response: dual-policy-conflict-missing

This file captures what a generic assistant produces WITHOUT the
autoscaling-policy-deployer skill loaded. The contrast proves the skill
catches the dual-policy trap (target tracking + step scaling on the
same metric causes oscillation) — the baseline blithely provisions both.

---

Sure, you can add a step scaling policy on top of your existing target
tracking. Here are the commands:

```bash
# Create the CloudWatch alarm
aws cloudwatch put-metric-alarm \
  --alarm-name billing-api-cpu-high \
  --metric-name CPUUtilization --namespace AWS/EC2 \
  --statistic Average --period 60 --evaluation-periods 2 --threshold 70 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=AutoScalingGroupName,Value=billing-api-asg \
  --alarm-actions <policy-arn>

# Create the step scaling policy
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name billing-api-asg \
  --policy-name cpu-step-scaling-out \
  --policy-type StepScaling \
  --adjustment-type PercentChangeInCapacity \
  --step-adjustments MetricIntervalLowerBound=0,ScalingAdjustment=50
```

Both policies will now work together for extra responsiveness under
high load.
