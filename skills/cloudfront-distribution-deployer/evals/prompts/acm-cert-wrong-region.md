# Eval prompt: acm-cert-wrong-region

Design a deployment plan for a production CloudFront distribution. Emit
the standard VERDICT block (DISTRIBUTION_SPEC, VERDICT, ARCHITECTURE,
CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- Origin: S3 REST (app-assets-eu.s3.eu-west-1.amazonaws.com)
- OAC for S3 origin
- Viewer protocol: redirect-to-https
- TLS minimum: TLSv1.2_2021
- ACM certificate: arn:aws:acm:eu-west-1:111111111111:certificate/wrong-region
  (covers app.eu.example.com)
- WAF: CLOUDFRONT scope in us-east-1
- Cache policy: CachingOptimized

Existing-account context: one prior distribution uses a us-east-1 ACM
cert successfully. The user (a junior engineer) mistakenly created this
new cert in eu-west-1, reasoning that the cert should be "co-located
with the S3 origin region." They have not yet attempted to deploy — they
want a deployment plan first.

Note: CloudFront is a global service but can ONLY read ACM certificates
from us-east-1. This is an AWS hard constraint, not a recommendation.
