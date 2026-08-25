# EC2 Instance Recovery - Diagnostic Commands

Load this reference before executing any live-account pre-flight.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws ec2 describe-instance-status --instance-ids <id> --include-all-
   instances` — capture `InstanceState`, `SystemStatus.Status`,
   `InstanceStatus.Status`, `Events` (scheduled maintenance).
2. `aws ec2 describe-instances --instance-ids <id>` — capture
   `InstanceType`, `Placement` (Affinity, GroupName, Tenancy),
   `RootDeviceType`, `BlockDeviceMappings`, `StateTransitionReason`,
   `CapacityReservationId`, `CapacityReservationSpecification`.
3. `aws autoscaling describe-auto-scaling-instances --instance-ids
   <id>` — capture ASG membership, `LifecycleState`, `HealthStatus`.
4. `aws ec2 describe-volumes --filters Name=attachment.instance-id,
   Values=<id>` — capture all EBS volume IDs and attachment state for
   rollback.
5. `aws ssm describe-instance-information --filters Key=InstanceIds,
   Values=<id>` — capture `PingStatus`, `AgentVersion`,
   `PlatformName`.
6. `aws cloudwatch describe-alarms-for-metric --namespace
   AWS/EC2 --metric-name StatusCheckFailed_System --dimensions
   Name=InstanceId,Value=<id>` — capture any existing recovery alarm.
7. `aws ec2 get-console-output --instance-id <id> --latest` — capture
   the last boot's console log for OS-level diagnosis.
