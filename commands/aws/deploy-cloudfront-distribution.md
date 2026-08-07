---
description: Provision a production-grade CloudFront distribution with OAC, WAF, TLS 1.2, security headers, geo restriction, edge compute, and logging.
nl_triggers:
  - "create a CloudFront distribution"
  - "provision a CDN distribution"
  - "configure OAC on my S3 origin"
  - "CloudFront with WAF"
  - "multi-origin failover distribution"
  - "Lambda@Edge vs CloudFront Functions"
  - "CloudFront cache policy"
  - "CloudFront security headers"
  - "CloudFront geo restriction"
  - "CloudFront continuous deployment"
  - "ACM certificate for CloudFront"
  - "price class CloudFront"
  - "deploy CloudFront in front of ALB"
  - "CloudFront distribution for S3 bucket"
routes_to: cloudfront-distribution-deployer
---

# /aws:deploy-cloudfront-distribution

Activate the `cloudfront-distribution-deployer` skill and produce a
deployment plan for a production-grade CloudFront distribution with
secure defaults.

## What it does

Reads a deployment specification (origin type, viewer protocol, TLS
requirements, WAF requirements, cache behavior, geo restriction, edge
compute, logging, price class) and produces an ordered deployment plan
with:

1. Pre-flight specification gate — validates origin, viewer protocol,
   ACM cert (region + ISSUED status), WAF scope, price class. Blocks
   deployment (PREREQUISITES_MISSING) on missing fields or ACM cert in
   wrong region.
2. Origin Access Control (OAC) for S3 origins — replaces legacy OAI,
   supports SSE-KMS, requires bucket policy with service-principal +
   AWS:SourceArn condition.
3. Custom origin (ALB, EC2, on-prem) — https-only OriginProtocolPolicy,
   custom headers for origin verification, TLSv1.2+ origin SSL.
4. Viewer protocol — redirect-to-https (default) or https-only (strict).
5. TLS minimum — TLSv1.2_2021 (AEAD-only ciphers, removes CBC-mode).
6. ACM certificate — MUST be in us-east-1 for CloudFront, covers all
   alternate domain names.
7. WAFv2 Web ACL — CLOUDFRONT scope in us-east-1, managed rule groups
   + rate-based rule.
8. Cache policy + origin request policy — managed policies as starting
   points (CachingOptimized, AllViewerExceptHostHeader).
9. Response headers policy — security headers (HSTS preload, CSP,
   X-Frame-Options DENY, X-Content-Type-Options).
10. Origin group — active-passive failover on HTTP status codes
    (500/502/503/504/403/404).
11. Geo restriction — whitelist (allowlist) or blacklist (blocklist).
12. Price class — 100 (NA+EU), 200 (mid), All (global).
13. Edge compute — CloudFront Functions (lightweight, sub-ms) vs
    Lambda@Edge (complex, network access).
14. Access logging — S3 standard with ACL grant to awslogsdelivery, or
    real-time logging to Kinesis Firehose.
15. Continuous deployment — staging distributions with percentage-based
    traffic shifting.

Emits a deterministic deployment plan per distribution:

```text
DISTRIBUTION_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Origin / Viewer protocol / TLS / WAF / Cache / Headers / Geo / Compute / Logs
CHECKLIST:
  [x] Origin is S3 REST with OAC (or custom HTTPS)
  [x] OriginAccessControlId set on S3 origin
  [x] Bucket policy updated to service-principal with AWS:SourceArn
  [x] MinimumProtocolVersion is TLSv1.2_2021
  [x] ACM cert in us-east-1, covers all aliases
  [x] WAFv2 Web ACL associated (CLOUDFRONT scope, us-east-1)
  ...
FINDINGS:
  - [INFO] Cost estimate
  - [WARN] Geo restriction is none — global
DEPLOY_COMMANDS:
  <ordered list of aws cloudfront create-* commands>
```

## When to invoke

Provide a deployment spec and ask any of:

- "provision a CloudFront distribution in front of my S3 bucket"
- "configure OAC on my S3 origin"
- "deploy CloudFront with WAF and security headers"
- "multi-origin failover distribution for DR"
- "CloudFront Function for SPA URL rewrite"
- "ACM certificate for CloudFront custom domain"
- "set up CloudFront continuous deployment"

A bare origin + domain + "deploy CloudFront" also routes here via the
orchestrator.

## Inputs

- **Required:** origin (S3 bucket name, ALB DNS, or origin group spec),
  viewer_protocol_policy (redirect-to-https or https-only), domain_names
  (alternate domain names), tls_certificate (ACM ARN in us-east-1),
  waf_association (true/false).
- **Optional:** cache_policy, origin_request_policy, response_headers_policy,
  geo_restriction, price_class, edge_compute (Functions vs Lambda@Edge),
  logging_destination, continuous_deployment.

## Outputs

- One VERDICT block per distribution (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- ARCHITECTURE summary with origin/TLS/WAF/cache/headers layout.
- CHECKLIST with all 14 deployment dimensions validated.
- FINDINGS with cost estimates and security-posture warnings.
- DEPLOY_COMMANDS with ordered `aws cloudfront create-*` commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 1 Deploy specialist for CloudFront edge delivery).
- `/aws:audit-cloudfront-distribution` for post-deployment security
  auditing (TLS, OAC, WAF, logging).
- `/aws:audit-wafv2-web-acl` for rule-level WAF analysis.
