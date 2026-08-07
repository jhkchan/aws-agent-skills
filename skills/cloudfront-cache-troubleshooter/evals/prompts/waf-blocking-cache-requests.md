# Eval prompt: waf-blocking-cache-requests

Diagnose the following CloudFront caching issue. Walk the cache diagnostic
decision tree and emit the standard VERDICT block (DISTRIBUTION, VERDICT,
ROOT_CAUSE, CACHE_ISSUE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A CloudFront distribution `E4D5E6F7G8` (`dabc.cloudfront.net`) returns
403 Forbidden on all requests to `/api/*`. The origin (ALB) returns 200
OK when accessed directly, bypassing CloudFront. The operations team
reports the application's API is down for all users behind CloudFront.

## Known facts

- `get-distribution-config` shows:
  - Cache behavior for `/api/*` with `CachePolicyId`: `CachingDisabled`
    (`4135ea2d-6df8-44a3-9df3-4b5a84be39ad` — dynamic API, no caching).
  - `WebACLId: 1a2b3c4d-5e6f-7890-abcd-ef1234567890`
  - No Lambda@Edge functions.
  - Origin: ALB `internal-alb-123.us-east-1.elb.amazonaws.com`.
- `curl -I https://internal-alb-123.us-east-1.elb.amazonaws.com/api/health`
  returns `200 OK` (origin is healthy).
- `curl -I https://dabc.cloudfront.net/api/health` returns:
  ```
  HTTP/2 403
  x-amzn-waf-action: BLOCK
  ```
- `wafv2 get-web-acl` for the attached web ACL:
  - Rule 1 (priority 1): rate-based rule, 100 requests per 5-minute
    window per IP, action: BLOCK.
  - Rule 2 (priority 2): SQL injection match, action: BLOCK.
  - Default action: ALLOW.
- The application has a health check that sends 200 requests per minute
  from a single NAT gateway IP (`203.0.113.50`). This health check
  exceeds the rate-based rule threshold of 100 requests per 5 minutes.
- WAF sample requests show the health-check requests from
  `203.0.113.50` being blocked by Rule 1 (rate-based).

## Symptom

403 Forbidden from CloudFront on all `/api/*` requests, including
legitimate user traffic. The WAF rate-based rule is blocking the NAT
gateway IP because the health check (200 requests/min) exceeds the
threshold (100 requests / 5 min). Once the IP is blocked, all traffic
from that NAT IP is blocked, including legitimate user traffic that
shares the same NAT egress IP.
