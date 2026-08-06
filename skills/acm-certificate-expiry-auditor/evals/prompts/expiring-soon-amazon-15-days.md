# Eval prompt: expiring-soon-amazon-15-days

Audit the following ACM certificate for expiry risk. Emit the standard
VERDICT block (CERTIFICATE, VERDICT, RISK, REASON, REMEDIATION) followed
by a single POSTURE SUMMARY.

Certificate ARN: arn:aws:acm:us-east-1:111111111111:certificate/expiring-soon-amazon-15-days
Certificate configuration:
  DomainName: api.example.com
  Type: AMAZON_ISSUED
  Status: ISSUED
  NotAfter: 2026-08-19T23:59:59Z
  RenewalEligibility: ELIGIBLE
  RenewalSummary:
    RenewalStatus: PENDING_AUTORENEWAL
    UpdatedAt: 2026-08-01T12:00:00Z
  KeyAlgorithm: RSA_2048
  DomainValidationOptions:
    - ValidationMethod: DNS
      ValidationStatus: SUCCESS
  InUseBy: []
Today is 2026-08-04.
