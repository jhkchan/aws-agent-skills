# Eval prompt: renewal-failed-caa-error

Audit the following ACM certificate for expiry risk. Emit the standard
VERDICT block (CERTIFICATE, VERDICT, RISK, REASON, REMEDIATION) followed
by a single POSTURE SUMMARY.

Certificate ARN: arn:aws:acm:us-east-1:111111111111:certificate/renewal-failed-caa-error
Certificate configuration:
  DomainName: www.example.com
  Type: AMAZON_ISSUED
  Status: ISSUED
  NotAfter: 2026-08-24T23:59:59Z
  RenewalEligibility: ELIGIBLE
  RenewalSummary:
    RenewalStatus: FAILED_AUTORENEWAL
    RenewalStatusReason: CAA_ERROR
    UpdatedAt: 2026-08-01T12:00:00Z
  KeyAlgorithm: RSA_2048
  DomainValidationOptions:
    - ValidationMethod: DNS
      ValidationStatus: SUCCESS
  InUseBy:
    - arn:aws:cloudfront::111111111111:distribution/E123ABCDEF
Today is 2026-08-04.
