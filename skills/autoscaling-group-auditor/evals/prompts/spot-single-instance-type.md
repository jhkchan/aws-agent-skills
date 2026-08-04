# Eval prompt: spot-single-instance-type

Audit the following Auto Scaling Group configuration for misconfigurations and
gaps. Emit the standard VERDICT block (ASG, VERDICT, REASON, FINDINGS,
REMEDIATION).

ASG name: prod-spot-worker-asg
LaunchTemplate:
  LaunchTemplateId: lt-0xyz789ghi012
  Version: "2"
  MetadataOptions:
    HttpTokens: required
LaunchConfigurationName: null
MinSize: 2
MaxSize: 10
DesiredCapacity: 4
AvailabilityZones: [us-east-1a, us-east-1b, us-east-1c]
HealthCheckType: EC2
HealthCheckGracePeriod: 300
TargetGroupARNs: []
LoadBalancerNames: []
MixedInstancesPolicy:
  LaunchTemplate:
    LaunchTemplateSpecification:
      LaunchTemplateId: lt-0xyz789ghi012
      Version: "2"
    Overrides:
      - InstanceType: c5.large
  InstancesDistribution:
    OnDemandAllocationStrategy: prioritized
    OnDemandBaseCapacity: 0
    OnDemandPercentageAboveBaseCapacity: 0
    SpotAllocationStrategy: capacity-optimized
CapacityRebalance:
  Enabled: false
TerminationPolicies: [Default]
SuspendedProcesses: []
