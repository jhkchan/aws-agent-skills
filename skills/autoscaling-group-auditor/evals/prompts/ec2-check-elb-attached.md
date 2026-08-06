# Eval prompt: ec2-check-elb-attached

Audit the following Auto Scaling Group configuration for misconfigurations and
gaps. Emit the standard VERDICT block (ASG, VERDICT, REASON, FINDINGS,
REMEDIATION).

ASG name: prod-backend-asg
LaunchTemplate:
  LaunchTemplateId: lt-0aaa111bbb222
  Version: "4"
  MetadataOptions:
    HttpTokens: required
LaunchConfigurationName: null
MinSize: 2
MaxSize: 4
DesiredCapacity: 4
AvailabilityZones: [us-east-1a]
HealthCheckType: EC2
HealthCheckGracePeriod: 300
TargetGroupARNs: [arn:aws:elasticloadbalancing:us-east-1:111111111111:targetgroup/backend-tg/def456]
LoadBalancerNames: []
MixedInstancesPolicy: null
CapacityRebalance:
  Enabled: false
TerminationPolicies: [Default]
SuspendedProcesses: []
