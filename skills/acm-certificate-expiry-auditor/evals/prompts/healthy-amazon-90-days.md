# Eval prompt: healthy-amazon-90-days

Audit the following ACM certificate for expiry risk. Emit the standard
VERDICT block (CERTIFICATE, VERDICT, RISK, REASON, REMEDIATION) followed
by a single POSTURE SUMMARY.

Certificate ARN: arn:aws:acm:us-east-1:111111111111:certificate/healthy-amazon-90-days
Certificate configuration:
  DomainName: app.example.com
  Type: AMAZON_ISSUED
  Status: ISSUED
  NotAfter: 2026-11-02T23:59:59Z
  RenewalEligibility: ELIGIBLE
  KeyAlgorithm: RSA_2048
  DomainValidationOptions:
    - ValidationMethod: DNS
      ValidationStatus: SUCCESS
  InUseBy:
    - arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/app-alb/ghi789
Today is 2026-08-04.
