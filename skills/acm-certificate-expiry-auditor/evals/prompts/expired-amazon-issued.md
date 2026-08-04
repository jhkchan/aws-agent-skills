# Eval prompt: expired-amazon-issued

Audit the following ACM certificate for expiry risk. Emit the standard
VERDICT block (CERTIFICATE, VERDICT, RISK, REASON, REMEDIATION) followed
by a single POSTURE SUMMARY.

Certificate ARN: arn:aws:acm:us-east-1:111111111111:certificate/expired-amazon-issued
Certificate configuration:
  DomainName: api.example.com
  Type: AMAZON_ISSUED
  Status: ISSUED
  NotAfter: 2026-07-15T23:59:59Z
  RenewalEligibility: ELIGIBLE
  KeyAlgorithm: RSA_2048
  InUseBy:
    - arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/prod-alb/abc123
Today is 2026-08-04.
