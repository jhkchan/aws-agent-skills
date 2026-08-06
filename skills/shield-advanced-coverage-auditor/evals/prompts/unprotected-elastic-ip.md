# Eval prompt: unprotected-elastic-ip

Audit the following AWS Shield Advanced configuration for DDoS coverage
posture. Emit the standard VERDICT block (SCOPE, VERDICT, REASON, FINDINGS,
REMEDIATION).

Account: 111111111111 (us-east-1)
SubscriptionState: ACTIVE

Internet-facing resource inventory:
  - Elastic IP eipalloc-abc222 (eip-unprotected-elastic-ip) associated with EC2 i-2222

Protections (from ListProtections):
  []

DRT access (from DescribeDRTAccess):
  RoleArn: arn:aws:iam::111111111111:role/AWSShieldDRTAccessRole
  LogBuckets: [shield-drt-logs]

ProactiveEngagement: ENABLED
EmergencyContactList:
  - EmailAddress: oncall@example.com
    PhoneNumber: "+15551234567"

WAF Web ACL associations: []
