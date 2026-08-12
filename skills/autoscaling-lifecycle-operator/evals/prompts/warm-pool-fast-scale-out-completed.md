# Eval prompt: warm-pool-fast-scale-out-completed

Plan the following Auto Scaling warm pool operation and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: configure-warm-pool
ASG: prod-web-asg
PoolMinSize: 3
MaxGroupPreparedCapacity: 5

```json
{
  "AsgMetadata": {
    "AutoScalingGroupName": "prod-web-asg",
    "MinSize": 2,
    "MaxSize": 20,
    "DesiredCapacity": 4,
    "LaunchTemplate": {"LaunchTemplateId": "lt-abc123", "Version": "2"}
  },
  "SubnetCheck": {
    "AvailableIPs": 200
  },
  "PostConfigVerification": {
    "DescribeWarmPool": {
      "PoolMinSize": 3,
      "MaxGroupPreparedCapacity": 5,
      "Instances": [
        {"InstanceId": "i-aaa", "State": "Stopped"},
        {"InstanceId": "i-bbb", "State": "Stopped"},
        {"InstanceId": "i-ccc", "State": "Stopped"}
      ]
    }
  }
}
```
