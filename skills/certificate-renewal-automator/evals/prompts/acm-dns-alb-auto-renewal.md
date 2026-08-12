# Eval prompt: acm-dns-alb-auto-renewal

Design a certificate renewal automation pipeline for the following ACM
certificate. Emit the standard RENEWAL block (CERTIFICATE,
CLASSIFICATION, DETECTION, RENEWAL_FLOW, VALIDATION, NOTIFICATION,
AUDIT, VERDICT, TEMPLATE).

Design reference: acm-dns-alb-auto-renewal
Account: 111111111111
Region: us-east-1

Certificate: www.example.com (arn:aws:acm:us-east-1:111111111111:certificate/abc-123)
Validation method: DNS (Route 53 CNAME _abc123.www.example.com -> _xyz789.acm-validations.aws.)
Status: ISSUED, RenewalEligibility: ELIGIBLE
Attached to: ALB listener arn:aws:elasticloadbalancing:us-east-1:111111111111:listener/app/prod-alb/xyz/lst-001
SAN domains: www.example.com, example.com
DaysToExpiry: 58
Route 53 hosted zone: Z1ABCDEF23456
