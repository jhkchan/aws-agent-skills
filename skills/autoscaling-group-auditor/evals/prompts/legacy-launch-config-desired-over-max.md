# Eval prompt: legacy-launch-config-desired-over-max

Audit the following Auto Scaling Group configuration for misconfigurations and
gaps. Emit the standard VERDICT block (ASG, VERDICT, REASON, FINDINGS,
REMEDIATION).

ASG name: legacy-batch-asg
LaunchTemplate: null
LaunchConfigurationName: legacy-batch-lc-2023
MinSize: 2
MaxSize: 4
DesiredCapacity: 6
AvailabilityZones: [us-east-1a, us-east-1b]
HealthCheckType: EC2
HealthCheckGracePeriod: 300
TargetGroupARNs: []
LoadBalancerNames: []
MixedInstancesPolicy: null
CapacityRebalance:
  Enabled: false
TerminationPolicies: [Default]
SuspendedProcesses: []
