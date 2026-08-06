# Eval prompt: drt-role-no-log-bucket

Audit the following AWS Shield Advanced configuration for DDoS coverage
posture. Emit the standard VERDICT block (SCOPE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 111111111111 (us-east-1)
SubscriptionState: ACTIVE

Internet-facing resource inventory:
  - ALB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/alb-drt-role-no-log-bucket/abc

Protections (from ListProtections):
  - ProtectionId: p-006
    Name: alb-protection-drt-role-no-log-bucket
    ResourceArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/alb-drt-role-no-log-bucket/abc
    HealthCheckIds: [arn:aws:route53:::healthcheck/hc-alb-drt-role-no-log-bucket]

DRT access (from DescribeDRTAccess):
  RoleArn: arn:aws:iam::111111111111:role/AWSShieldDRTAccessRole
  LogBuckets: []

ProactiveEngagement: ENABLED
EmergencyContactList:
  - EmailAddress: oncall@example.com
    PhoneNumber: "+15551234567"

WAF Web ACL associations:
  - ALB arn:...:loadbalancer/app/alb-drt-role-no-log-bucket/abc -> WebACLArn arn:aws:wafv2:us-east-1:111111111111:regional/webacl/shield-waf/abc
