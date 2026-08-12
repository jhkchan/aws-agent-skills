# Eval prompt: diagnose-stuck-pending-wait-review-required

Plan the following Auto Scaling lifecycle diagnostic operation and emit
the standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, NOTES).

Operation: diagnose-stuck
ASG: prod-api-asg

```json
{
  "AsgMetadata": {
    "AutoScalingGroupName": "prod-api-asg",
    "DesiredCapacity": 6,
    "LifecycleHooks": [
      {
        "LifecycleHookName": "api-bootstrap-hook",
        "LifecycleTransition": "autoscaling:EC2_INSTANCE_LAUNCHING",
        "HeartbeatTimeout": 3600,
        "DefaultResult": "CONTINUE",
        "NotificationTargetARN": "arn:aws:lambda:us-east-1:111111111111:function:api-lifecycle-action"
      }
    ]
  },
  "StuckInstance": {
    "InstanceId": "i-xxx",
    "LifecycleState": "Pending:Wait",
    "DurationInWait": "42 minutes"
  },
  "LambdaMetadata": {
    "FunctionName": "api-lifecycle-action",
    "State": "Active",
    "Timeout": 30
  },
  "CloudWatchLogs": {
    "LastError": "TASK FAILED: Task timed out after 30.00 seconds",
    "LastInvocation": "42 minutes ago"
  }
}
```
