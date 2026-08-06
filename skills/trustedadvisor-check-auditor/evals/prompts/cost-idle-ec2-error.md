# Eval prompt: cost-idle-ec2-error

Audit the following Trusted Advisor check result for operational and
security risk. Emit the standard VERDICT block (CHECK, VERDICT, REASON,
FINDINGS, REMEDIATION).

Account metadata:
  Support tier: Business
  Total checks available: 115

Check id: cost-idle-ec2-error
Check name: Idle EC2 Instances
Category: Cost Optimization
Status: error
Timestamp: 2026-08-05T08:00:00Z (4 hours ago)
Excluded resources: none

Flagged resources:
  - resourceId: i-cost-idle-ec2-error-01
    region: us-east-1
    status: error
    metadata:
      Instance Type: m5.large
      Average CPU: 3%
      Days Idle: 14
      Estimated Monthly Savings: $140
  - resourceId: i-cost-idle-ec2-error-02
    region: us-east-1
    status: error
    metadata:
      Instance Type: m5.xlarge
      Average CPU: 2%
      Days Idle: 21
      Estimated Monthly Savings: $170
