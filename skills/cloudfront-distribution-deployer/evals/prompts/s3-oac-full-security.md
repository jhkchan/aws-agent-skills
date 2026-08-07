# Eval prompt: s3-oac-full-security

Design a deployment plan for a production CloudFront distribution. Emit
the standard VERDICT block (DISTRIBUTION_SPEC, VERDICT, ARCHITECTURE,
CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- Origin: S3 REST (prod-app-assets.s3.us-east-1.amazonaws.com)
- OAC for S3 origin (replaces legacy OAI; signing behavior: always)
- Viewer protocol: redirect-to-https
- TLS minimum: TLSv1.2_2021
- ACM certificate: arn:aws:acm:us-east-1:111111111111:certificate/abc-123
  (ISSUED, covers app.example.com and www.example.com)
- WAF: WAFv2 CLOUDFRONT scope in us-east-1, CommonRuleSet +
  AmazonIpReputationList + rate-based rule (2000 req/5min per IP)
- Cache policy: CachingOptimized (static assets)
- Origin request policy: none (S3 origin, no forwarding needed)
- Response headers: security headers policy — HSTS max-age 63072000
  preload, X-Frame-Options DENY, X-Content-Type-Options nosniff,
  CSP `default-src 'self'; object-src 'none'`
- Geo: whitelist US, CA, GB, DE, FR
- Price class: PriceClass_100
- Edge compute: CloudFront Function for SPA URL rewrite (`/*` to
  `/index.html` for client-side routing)
- Logging: S3 standard to prod-cf-logs.s3.amazonaws.com with ACL grant
  to awslogsdelivery canonical ID

Existing-account context: two other distributions use us-east-1 ACM certs
successfully. No Direct Connect or Site-to-Site VPN. The S3 bucket
prod-app-assets exists in us-east-1, is currently private (BlockPublicAccess
enabled, no public ACLs), and has not yet been configured with OAC.
