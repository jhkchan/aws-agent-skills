# Eval prompt: origin-group-failover

Design a deployment plan for a multi-region failover CloudFront
distribution. Emit the standard VERDICT block (DISTRIBUTION_SPEC,
VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- Primary origin: prod-alb-us-east-1.us-east-1.elb.amazonaws.com (HTTPS,
  ACM cert on ALB listener)
- Secondary origin (DR): prod-alb-us-west-2.us-west-2.elb.amazonaws.com
  (HTTPS, ACM cert on ALB listener)
- Origin group: active-passive failover on status codes
  500, 502, 503, 504, 403, 404
- Origin protocol policy: https-only on both origins
- Origin SSL protocols: TLSv1.2 only on both
- Custom origin headers on both: `X-Origin-Verify: <shared-secret>`
- Viewer protocol: https-only (strict environment, query strings carry
  auth tokens that must never transit HTTP)
- TLS minimum: TLSv1.2_2021
- ACM cert (viewer): arn:aws:acm:us-east-1:111111111111:certificate/api-cert
  (covers api.example.com)
- WAF: CLOUDFRONT scope in us-east-1, CommonRuleSet + BotControlRuleSet +
  rate-based (5000 req/5min per IP)
- Cache policy: CachingDisabled (dynamic API)
- Origin request policy: AllViewerExceptHostHeader
- Response headers: security headers policy (HSTS 2yr preload, CSP,
  X-Frame-Options DENY)
- Geo: none (global API)
- Price class: PriceClass_All
- Logging: real-time logging to Kinesis Firehose → OpenSearch (for
  anomaly detection on origin switch-over events)

Existing-account context: both ALBs have valid ACM-managed HTTPS
listeners. The DR ALB in us-west-2 is currently warm (scaled to 30%
capacity). Both ALBs validate the X-Origin-Verify header in a listener
rule.
