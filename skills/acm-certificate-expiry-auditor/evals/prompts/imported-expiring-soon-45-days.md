# Eval prompt: imported-expiring-soon-45-days

Audit the following ACM certificate for expiry risk. Emit the standard
VERDICT block (CERTIFICATE, VERDICT, RISK, REASON, REMEDIATION) followed
by a single POSTURE SUMMARY.

Certificate ARN: arn:aws:acm:us-east-1:111111111111:certificate/imported-expiring-soon-45-days
Certificate configuration:
  DomainName: portal.example.com
  Type: IMPORTED
  Status: ISSUED
  NotAfter: 2026-09-18T23:59:59Z
  RenewalEligibility: INELIGIBLE
  KeyAlgorithm: RSA_2048
  InUseBy:
    - arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/portal-alb/def456
Today is 2026-08-04.
