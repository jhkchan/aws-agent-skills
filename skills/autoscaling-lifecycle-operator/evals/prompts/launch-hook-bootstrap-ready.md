# Eval prompt: launch-hook-bootstrap-ready

Plan the following Auto Scaling lifecycle hook operation and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: add-launch-hook
ASG: prod-web-asg
Hook name: web-bootstrap-hook
HeartbeatTimeout: 300
DefaultResult: CONTINUE
Notification target: arn:aws:lambda:us-east-1:111111111111:function:web-lifecycle-action

```json
{
  "AsgMetadata": {
    "AutoScalingGroupName": "prod-web-asg",
    "MinSize": 2,
    "MaxSize": 20,
    "DesiredCapacity": 4,
    "LaunchTemplate": {"LaunchTemplateId": "lt-abc123", "Version": "2"},
    "TargetGroupARNs": ["arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/web-tg/abc"],
    "HealthCheckType": "ELB",
    "HealthCheckGracePeriod": 600,
    "ServiceLinkedRoleARN": "arn:aws:iam::111111111111:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling"
  },
  "ExistingLifecycleHooks": [],
  "LambdaMetadata": {
    "FunctionName": "web-lifecycle-action",
    "State": "Active",
    "Runtime": "python3.12",
    "Timeout": 120
  },
  "LambdaRolePolicies": [
    "AWSLambdaBasicExecutionRole",
    "autoscaling:CompleteLifecycleAction on arn:aws:autoscaling:us-east-1:111111111111:autoScalingGroup:..."
  ]
}
```
