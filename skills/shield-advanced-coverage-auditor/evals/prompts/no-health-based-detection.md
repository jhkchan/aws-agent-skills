# Eval prompt: no-health-based-detection

Audit the following AWS Shield Advanced configuration for DDoS coverage
posture. Emit the standard VERDICT block (SCOPE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 111111111111 (us-east-1)
SubscriptionState: ACTIVE

Internet-facing resource inventory:
  - ALB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/alb-no-health-based-detection/abc

Protections (from ListProtections):
  - ProtectionId: p-004
    Name: alb-protection-no-health-based-detection
    ResourceArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/alb-no-health-based-detection/abc
    HealthCheckIds: []

DRT access (from DescribeDRTAccess):
  RoleArn: arn:aws:iam::111111111111:role/AWSShieldDRTAccessRole
  LogBuckets: [shield-drt-logs]

ProactiveEngagement: ENABLED
EmergencyContactList:
  - EmailAddress: oncall@example.com
    PhoneNumber: "+15551234567"

WAF Web ACL associations:
  - ALB arn:...:loadbalancer/app/alb-no-health-based-detection/abc -> WebACLArn arn:aws:wafv2:us-east-1:111111111111:regional/webacl/shield-waf/abc
