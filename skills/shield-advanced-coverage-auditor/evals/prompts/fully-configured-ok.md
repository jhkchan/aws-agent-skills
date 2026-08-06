# Eval prompt: fully-configured-ok

Audit the following AWS Shield Advanced configuration for DDoS coverage
posture. Emit the standard VERDICT block (SCOPE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 111111111111 (us-east-1)
SubscriptionState: ACTIVE

Internet-facing resource inventory:
  - CloudFront distribution d-abc123 (app-cf-fully-configured-ok)
  - ALB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/alb-fully-configured-ok/xyz

Protections (from ListProtections):
  - ProtectionId: p-001
    Name: alb-protection-fully-configured-ok
    ResourceArn: arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/alb-fully-configured-ok/xyz
    HealthCheckIds: [arn:aws:route53:::healthcheck/hc-alb-fully-configured-ok]

DRT access (from DescribeDRTAccess):
  RoleArn: arn:aws:iam::111111111111:role/AWSShieldDRTAccessRole
  LogBuckets: [shield-drt-alb-logs]

ProactiveEngagement: ENABLED
EmergencyContactList:
  - EmailAddress: oncall@example.com
    PhoneNumber: "+15551234567"
    ContactNotes: "24/7 NOC"

WAF Web ACL associations:
  - ALB arn:...:loadbalancer/app/alb-fully-configured-ok/xyz -> WebACLArn arn:aws:wafv2:us-east-1:111111111111:regional/webacl/shield-alb-waf/def
