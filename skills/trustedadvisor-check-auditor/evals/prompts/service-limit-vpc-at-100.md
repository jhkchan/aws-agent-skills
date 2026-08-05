# Eval prompt: service-limit-vpc-at-100

Audit the following Trusted Advisor check result for operational and
security risk. Emit the standard VERDICT block (CHECK, VERDICT, REASON,
FINDINGS, REMEDIATION).

Account metadata:
  Support tier: Business
  Total checks available: 115

Check id: service-limit-vpc-at-100
Check name: VPC Limit
Category: Service Limits
Status: error
Timestamp: 2026-08-05T11:00:00Z (1 hour ago)
Excluded resources: none

Flagged resources:
  - resourceId: vpc-service-limit-vpc-at-100
    region: us-east-1
    status: error
    metadata:
      Limit: 5
      Current Usage: 5
      Service: Amazon VPC
