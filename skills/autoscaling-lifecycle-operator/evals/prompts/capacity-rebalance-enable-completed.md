# Eval prompt: capacity-rebalance-enable-completed

Plan the following Auto Scaling capacity rebalance operation and emit
the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, NOTES).

Operation: enable-capacity-rebalance
ASG: prod-spot-asg

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
    "CapacityRebalance": false
  },
  "ExistingLifecycleHooks": [
    {
      "LifecycleHookName": "spot-drain-hook",
      "LifecycleTransition": "autoscaling:EC2_INSTANCE_TERMINATING",
      "HeartbeatTimeout": 90,
      "DefaultResult": "CONTINUE"
    }
  ],
  "PostConfigVerification": {
    "CapacityRebalance": true
  }
}
```
