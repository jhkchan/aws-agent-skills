# Eval prompt: alb-custom-origin-deploy

Design a deployment plan for a CloudFront distribution in front of an
ALB. Emit the standard VERDICT block (DISTRIBUTION_SPEC, VERDICT,
ARCHITECTURE, CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- Origin: ALB (prod-alb.us-east-1.elb.amazonaws.com) with HTTPS listener
  on 443 (ACM-managed cert on the ALB listener)
- Origin protocol policy: https-only
- Origin SSL protocols: TLSv1.2 only
- Custom origin header: `X-Origin-Verify: <shared-secret>` (ALB listener
  rule validates this header to confirm CloudFront-origin traffic)
- Viewer protocol: redirect-to-https
- TLS minimum: TLSv1.2_2021
- ACM cert (viewer): arn:aws:acm:us-east-1:111111111111:certificate/def-456
  (covers app.example.com)
- WAF: CLOUDFRONT scope in us-east-1, CommonRuleSet + SQLiRuleSet +
  rate-based (2000 req/5min per IP)
- Cache policy: CachingDisabled (dynamic API responses, no caching)
- Origin request policy: AllViewerExceptHostHeader (forward all viewer
  info to ALB; ALB determines Host)
- Response headers: security headers policy (HSTS 2yr, CSP
  `default-src 'self'`, X-Frame-Options DENY)
- Geo: none (global B2B SaaS)
- Price class: PriceClass_All
- Logging: real-time logging to Kinesis Firehose → S3

Existing-account context: the ALB has an HTTPS listener with a public
ACM cert (not self-signed). The ALB security group allows inbound 443
from 0.0.0.0/0 but will be tightened to allow only CloudFront managed
prefix list after deployment.
