# Eval prompt: security-sg-open-error

Audit the following Trusted Advisor check result for operational and
security risk. Emit the standard VERDICT block (CHECK, VERDICT, REASON,
FINDINGS, REMEDIATION).

Account metadata:
  Support tier: Business
  Total checks available: 115

Check id: security-sg-open-error
Check name: Security Groups - Specific Ports Unrestricted
Category: Security
Status: error
Timestamp: 2026-08-05T10:00:00Z (2 hours ago)
Excluded resources: none

Flagged resources:
  - resourceId: sg-security-sg-open-error
    region: us-east-1
    status: error
    metadata:
      Protocol: TCP
      Port: 22
      Source: 0.0.0.0/0
      Recommendation: Restrict to known CIDR range
