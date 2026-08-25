# EC2 Spot Interruption - Diagnostic Commands

Load this reference before executing any live-account pre-flight.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws ec2 describe-spot-instance-requests --spot-instance-request-id
   <id>` — confirm `State: active`; capture `InstanceId`,
   `InstanceInterruptionBehavior`, `InstanceType`, `AvailabilityZone`.
2. `aws ec2 describe-spot-fleet-requests --spot-fleet-request-ids <id>`
   — capture `AllocationStrategy`, `TargetCapacity`,
   `FulfilledCapacity`, `LaunchTemplateConfigs.Overrides`
   (diversification list).
3. `aws events describe-rule --name <rule-name>` — confirm `ENABLED`.
   `aws events list-targets-by-rule` — confirm target (SQS or Lambda).
4. `aws sqs get-queue-attributes --queue-url <url>
   --attribute-names All` — capture queue depth,
   `ApproximateAgeOfOldestMessage`, `RedrivePolicy`.
5. `aws lambda get-function-configuration --function-name <fn>` —
   confirm `State: Active`, `Timeout >= 60`. `aws lambda
   get-function-concurrency` — confirm reserved concurrency not 0.
6. `aws elbv2 describe-target-group-attributes --target-group-arn <arn>`
   — capture `deregistration_delay.timeout_seconds`.
   `aws elbv2 describe-target-health` — confirm instance is registered.
7. `aws autoscaling describe-auto-scaling-groups
   --auto-scaling-group-names <name>` — capture `CapacityRebalance`,
   `MixedInstancesPolicy`, lifecycle hooks.
