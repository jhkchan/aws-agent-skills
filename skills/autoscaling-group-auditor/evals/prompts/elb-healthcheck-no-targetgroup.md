# Eval prompt: elb-healthcheck-no-targetgroup

Audit the following Auto Scaling Group configuration for misconfigurations and
gaps. Emit the standard VERDICT block (ASG, VERDICT, REASON, FINDINGS,
REMEDIATION).

ASG name: prod-web-asg
LaunchTemplate:
  LaunchTemplateId: lt-0abc123def456
  Version: "3"
  MetadataOptions:
    HttpTokens: required
LaunchConfigurationName: null
MinSize: 2
MaxSize: 6
DesiredCapacity: 4
AvailabilityZones: [us-east-1a, us-east-1b, us-east-1c]
HealthCheckType: ELB
HealthCheckGracePeriod: 300
TargetGroupARNs: []
LoadBalancerNames: []
MixedInstancesPolicy: null
CapacityRebalance:
  Enabled: false
TerminationPolicies: [Default]
SuspendedProcesses: []
