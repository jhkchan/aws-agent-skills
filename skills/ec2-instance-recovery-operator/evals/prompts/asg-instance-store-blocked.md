# Eval prompt: asg-instance-store-blocked

Plan the following EC2 instance stop/start recovery and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS,
STEPS, POST_VERIFY, NOTES).

Operation: stop-start
Instance: i-0abcdef1234567890

```json
{
  "InstanceStatus": {
    "State": "running",
    "SystemStatus": {"Status": "impaired"},
    "InstanceStatus": {"Status": "ok"}
  },
  "InstanceDetails": {
    "RootDeviceType": "instance-store",
    "Placement": {"Tenancy": "default"}
  },
  "AsgMembership": {
    "AutoScalingGroupName": "prod-web-asg",
    "LifecycleState": "InService",
    "HealthStatus": "Healthy"
  }
}
```
