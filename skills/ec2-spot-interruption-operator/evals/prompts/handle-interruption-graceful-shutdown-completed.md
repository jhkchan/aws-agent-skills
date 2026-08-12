# Eval prompt: handle-interruption-graceful-shutdown-completed

Handle the following live Spot Instance Interruption Warning and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: handle-interruption
Event: EC2 Spot Instance Interruption Warning
Instance: i-0abc123def456
Instance action: terminate
Event time: 2026-08-11T14:23:00Z (105 seconds remaining in 2-min window)

```json
{
  "InstanceMetadata": {
    "InstanceType": "m6a.large",
    "AvailabilityZone": "us-east-1a",
    "SpotInstanceRequestId": "sir-abc123"
  },
  "SpotFleet": "sfr-prod-web (AllocationStrategy: capacity-optimized)",
  "ASG": "prod-web-asg (CapacityRebalance: true)",
  "TargetGroup": "arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/prod-web-tg/...",
  "GracefulShutdownLambda": {
    "FunctionName": "prod-spot-shutdown",
    "State": "Active",
    "Timeout": 90,
    "ReservedConcurrentExecutions": 10
  },
  "ELBDeregistrationDelay": 45,
  "ASGLifecycleHook": "spot-termination-hook (HeartbeatTimeout: 120)",
  "ExecutionResults": {
    "LambdaInvoked": "14:23:01Z — SUCCESS",
    "InstanceDeregistered": "14:23:03Z",
    "CheckpointWritten": "s3://prod-checkpoints/i-0abc123def456/state.json at 14:23:38Z",
    "ELBTargetUnused": "14:23:48Z",
    "InstanceTerminated": "14:25:00Z",
    "ReplacementLaunched": "i-0new456 (m6a.large, us-east-1b) at 14:25:15Z",
    "ReplacementRunning": "14:27:45Z",
    "ReplacementHealthy": "14:28:30Z"
  },
  "PostVerification": {
    "SpotFleetFulfilledCapacity": "10 (matches TargetCapacity)",
    "ELB5XX": "no spike",
    "ApplicationResumedFromCheckpoint": true
  }
}
```
