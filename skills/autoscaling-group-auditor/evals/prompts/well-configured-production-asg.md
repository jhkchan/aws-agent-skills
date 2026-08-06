# Eval prompt: well-configured-production-asg

Audit the following Auto Scaling Group configuration for misconfigurations and
gaps. Emit the standard VERDICT block (ASG, VERDICT, REASON, FINDINGS,
REMEDIATION).

ASG name: prod-frontend-asg
LaunchTemplate:
  LaunchTemplateId: lt-0prod123template
  Version: "5"
  MetadataOptions:
    HttpTokens: required
LaunchConfigurationName: null
MinSize: 2
MaxSize: 10
DesiredCapacity: 4
AvailabilityZones: [us-east-1a, us-east-1b, us-east-1c]
HealthCheckType: ELB
HealthCheckGracePeriod: 300
TargetGroupARNs: [arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/frontend-tg/ghi789]
LoadBalancerNames: []
MixedInstancesPolicy:
  LaunchTemplate:
    LaunchTemplateSpecification:
      LaunchTemplateId: lt-0prod123template
      Version: "5"
    Overrides:
      - InstanceType: c5.large
      - InstanceType: c5a.large
      - InstanceType: m5.large
      - InstanceType: m5a.large
  InstancesDistribution:
    OnDemandAllocationStrategy: prioritized
    OnDemandBaseCapacity: 2
    OnDemandPercentageAboveBaseCapacity: 50
    SpotAllocationStrategy: capacity-optimized
CapacityRebalance:
  Enabled: true
TerminationPolicies: [Default]
SuspendedProcesses: []
