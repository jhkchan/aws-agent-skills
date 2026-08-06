# Eval prompt: imdsv2-gap-short-grace

Audit the following Auto Scaling Group configuration for misconfigurations and
gaps. Emit the standard VERDICT block (ASG, VERDICT, REASON, FINDINGS,
REMEDIATION).

ASG name: staging-api-asg
LaunchTemplate:
  LaunchTemplateId: lt-0def456abc789
  Version: "1"
  MetadataOptions:
    HttpTokens: optional
LaunchConfigurationName: null
MinSize: 2
MaxSize: 10
DesiredCapacity: 4
AvailabilityZones: [us-east-1a, us-east-1b]
HealthCheckType: ELB
HealthCheckGracePeriod: 30
TargetGroupARNs: [arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/api-tg/abc123]
LoadBalancerNames: []
MixedInstancesPolicy:
  LaunchTemplate:
    LaunchTemplateSpecification:
      LaunchTemplateId: lt-0def456abc789
      Version: "1"
    Overrides:
      - InstanceType: c5.large
      - InstanceType: c5a.large
      - InstanceType: m5.large
  InstancesDistribution:
    OnDemandAllocationStrategy: prioritized
    OnDemandBaseCapacity: 2
    OnDemandPercentageAboveBaseCapacity: 70
    SpotAllocationStrategy: capacity-optimized
CapacityRebalance:
  Enabled: true
TerminationPolicies: [Default]
SuspendedProcesses: []
