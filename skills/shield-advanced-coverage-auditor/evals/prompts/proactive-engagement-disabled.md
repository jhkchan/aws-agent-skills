# Eval prompt: proactive-engagement-disabled

Audit the following AWS Shield Advanced configuration for DDoS coverage
posture. Emit the standard VERDICT block (SCOPE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 111111111111 (us-east-1)
SubscriptionState: ACTIVE

Internet-facing resource inventory:
  - ALB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/alb-proactive-engagement-disabled/abc

Protections (from ListProtections):
  - ProtectionId: p-005
    Name: alb-protection-proactive-engagement-disabled
    ResourceArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/alb-proactive-engagement-disabled/abc
    HealthCheckIds: [arn:aws:route53:::healthcheck/hc-alb-proactive-engagement-disabled]

DRT access (from DescribeDRTAccess):
  RoleArn: arn:aws:iam::111111111111:role/AWSShieldDRTAccessRole
  LogBuckets: [shield-drt-logs]

ProactiveEngagement: DISABLED
EmergencyContactList: []

WAF Web ACL associations:
  - ALB arn:...:loadbalancer/app/alb-proactive-engagement-disabled/abc -> WebACLArn arn:aws:wafv2:us-east-1:111111111111:regional/webacl/shield-waf/abc
