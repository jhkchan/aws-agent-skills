# Eval prompt: terminate-hook-spot-timeout-review-required

Plan the following Auto Scaling lifecycle hook operation and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: add-terminate-hook
ASG: prod-spot-asg
Hook name: spot-drain-hook
HeartbeatTimeout: 3600
DefaultResult: CONTINUE
Notification target: arn:aws:lambda:us-east-1:111111111111:function:spot-drain-action

```json
{
  "AsgMetadata": {
    "AutoScalingGroupName": "prod-spot-asg",
    "MinSize": 0,
    "MaxSize": 10,
    "DesiredCapacity": 5,
    "MixedInstancesPolicy": {
      "InstancesDistribution": {
        "OnDemandPercentageAboveBaseCapacity": 0,
        "SpotAllocationStrategy": "capacity-optimized"
      }
    },
    "CapacityRebalance": true
  }
}
```
