# Diagnostic Commands — Auto Scaling Policy Deployer

## Step 9 — post-deploy verification command listing

```bash
aws autoscaling describe-policies --auto-scaling-group-name <ASG>
aws autoscaling describe-scheduled-actions --auto-scaling-group-name <ASG>
aws autoscaling describe-warm-pool --auto-scaling-group-name <ASG>
aws autoscaling describe-instance-refreshes --auto-scaling-group-name <ASG>
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <ASG> \
  --query 'AutoScalingGroups[].{CapacityRebalance:CapacityRebalance,MIP:MixedInstancesPolicy}'
aws cloudwatch describe-alarms --alarm-name-prefix <ASG>
aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average
```

For predictive scaling, additionally verify the forecast is non-empty:

```bash
aws autoscaling describe-scaling-policies --auto-scaling-group-name <ASG> \
  --policy-names predictive-cpu-forecast \
  --query 'ScalingPolicies[].PredictiveScalingConfiguration'
```
