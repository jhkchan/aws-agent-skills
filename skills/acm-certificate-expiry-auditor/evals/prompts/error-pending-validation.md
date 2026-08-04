# Eval prompt: error-pending-validation

Audit the following ACM certificate for expiry risk. Emit the standard
VERDICT block (CERTIFICATE, VERDICT, RISK, REASON, REMEDIATION) followed
by a single POSTURE SUMMARY.

Certificate ARN: arn:aws:acm:us-east-1:111111111111:certificate/error-pending-validation
Certificate configuration:
  DomainName: new.example.com
  Type: AMAZON_ISSUED
  Status: PENDING_VALIDATION
  NotAfter: null
  RenewalEligibility: INELIGIBLE
  KeyAlgorithm: RSA_2048
  DomainValidationOptions:
    - ValidationMethod: DNS
      ValidationStatus: PENDING_VALIDATION
  InUseBy: []
Today is 2026-08-04.
