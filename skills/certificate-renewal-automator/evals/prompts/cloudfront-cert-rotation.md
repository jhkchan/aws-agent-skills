# Eval prompt: cloudfront-cert-rotation

Design a certificate renewal automation pipeline for the following
CloudFront distribution certificate. Emit the standard RENEWAL block
(CERTIFICATE, CLASSIFICATION, DETECTION, RENEWAL_FLOW, VALIDATION,
NOTIFICATION, AUDIT, VERDICT, TEMPLATE).

Design reference: cloudfront-cert-rotation
Account: 111111111111
Region: us-east-1

Certificate: cdn.example.com (arn:aws:acm:us-east-1:111111111111:certificate/cf-789)
Validation method: DNS
Status: ISSUED, RenewalEligibility: ELIGIBLE
Attached to: CloudFront distribution E1ABCDEF23456
SAN domains: cdn.example.com, assets.example.com
DaysToExpiry: 42
Current MinimumProtocolVersion: TLSv1.2_2021
