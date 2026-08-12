# Eval prompt: san-validation-gap

Design a certificate renewal automation pipeline for the following SAN
certificate. Emit the standard RENEWAL block (CERTIFICATE,
CLASSIFICATION, DETECTION, RENEWAL_FLOW, VALIDATION, NOTIFICATION,
AUDIT, VERDICT, GAP, TEMPLATE).

Design reference: san-validation-gap
Account: 111111111111
Region: us-east-1

Certificate: multi.example.com (arn:aws:acm:us-east-1:111111111111:certificate/san-001)
Validation method: DNS
SAN domains: multi.example.com, api.example.com, cdn.example.com
Status: ISSUED, RenewalEligibility: INELIGIBLE
Attached to: ALB listener
DaysToExpiry: 25

Note: The DNS validation CNAME for cdn.example.com was deleted during
a Route 53 zone cleanup. CNAMEs for multi.example.com and
api.example.com are present.
