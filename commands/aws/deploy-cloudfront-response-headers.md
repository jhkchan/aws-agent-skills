---
description: Provision CloudFront response headers policies — security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy), CORS (origins, methods, headers, credentials, preflight), custom headers, removal headers, and managed policies (SecurityHeadersPolicy, SimpleCORS, CORS-with-preflight-and-SecurityHeadersPolicy).
nl_triggers:
  - "create CloudFront response headers policy"
  - "CloudFront security headers"
  - "CloudFront CSP"
  - "CloudFront Content-Security-Policy"
  - "CloudFront HSTS"
  - "CloudFront Strict-Transport-Security"
  - "CloudFront X-Frame-Options"
  - "CloudFront X-Content-Type-Options"
  - "CloudFront Referrer-Policy"
  - "CloudFront Permissions-Policy"
  - "CloudFront CORS"
  - "CloudFront access-control-allow-origin"
  - "CloudFront preflight"
  - "CloudFront managed SecurityHeadersPolicy"
  - "CloudFront SimpleCORS"
  - "CloudFront remove Server header"
  - "CloudFront remove X-Powered-By"
  - "CloudFront Cache-Control header"
  - "attach response headers policy to distribution"
  - "harden CloudFront HTTP response headers"
routes_to: cloudfront-response-headers-deployer
---

# /aws:deploy-cloudfront-response-headers

Activate the `cloudfront-response-headers-deployer` skill and produce a
deployment plan for a CloudFront response headers policy with secure
defaults.

## What it does

Reads a deployment specification (header requirements: security headers
+ values, CORS origin/methods/headers, custom headers, removal headers,
managed vs custom policy) and produces an ordered deployment plan with:

1. Pre-flight specification gate — validates target distribution state
   (`Deployed`), existing policy attachments, origin HTTPS reachability,
   CSP compatibility with site script inventory, HSTS subdomain scope.
   Blocks deployment (PREREQUISITES_MISSING) on missing fields, CORS
   `*` + credentials, or `InProgress` distribution state.
2. Security headers — Content-Security-Policy (default-src 'self';
   object-src 'none'; frame-ancestors 'none'; base-uri 'self'),
   Strict-Transport-Security (max-age 63072000; includeSubDomains;
   preload in production), X-Frame-Options DENY, X-Content-Type-Options
   nosniff, Referrer-Policy strict-origin-when-cross-origin,
   Permissions-Policy (camera, microphone, geolocation, payment
   disabled).
3. CORS configuration — specific origins or `*` (NOT with credentials),
   methods, headers, expose-headers, credentials, max-age.
4. Custom headers — Cache-Control, X-Custom, X-Service-Version (override
   origin values).
5. Removal headers — X-Powered-By, X-AspNet-Version, X-AspNetMvc-Version
   (Server and Via cannot be removed).
6. Managed policy selection — SecurityHeadersPolicy (fixed ID
   `0857826db9cffff310d5ad62955c9c26`), SimpleCORS,
   CORS-with-preflight-and-SecurityHeadersPolicy,
   CORSAndHTTPSecurityHeadersPolicy.
7. Distribution attach — ETag-matched update-distribution to set
   ResponseHeadersPolicyId on the target cache behavior.

Emits a deterministic deployment plan per policy:

```text
OPERATION: <create | update | attach | audit>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <policy-name>
REQUIREMENTS:
  - [PASS] <requirement description>
  - [FAIL] <requirement description> — <gap>
IAC_TEMPLATE: <CloudFormation / Terraform template>
MANUAL_GAPS:
  - GAP: <gap description>
    REMEDIATION: <exact CLI or IaC snippet>
    REASON: <why this cannot be automated>
NOTES: <managed policy version, attach-vs-embed, distribution deploy state>
```

## When to invoke

Provide a deployment spec and ask any of:

- "add security headers to my CloudFront distribution"
- "configure CSP on my distribution"
- "set up CORS for credentialed cross-origin requests"
- "attach the managed SecurityHeadersPolicy"
- "remove X-Powered-By from my distribution responses"
- "add HSTS preload to my production CDN"
- "set Permissions-Policy to disable camera and microphone"
- "configure Cache-Control via response headers policy"

A bare distribution ID + "add security headers" also routes here via the
orchestrator.

## Inputs

- **Required:** target distribution ID (or "create new"), target cache
  behavior, header requirements (security / CORS / custom / removal).
- **Optional:** managed policy name (vs. custom), CSP directives, CORS
  origin list, credentials flag, preflight flag, HSTS scope, custom
  header key-value pairs, removal header list.

## Outputs

- One VERDICT block per policy (READY_TO_DEPLOY or PREREQUISITES_MISSING).
- REQUIREMENTS list with [PASS] / [FAIL] per requirement.
- Inline CloudFormation or Terraform template (READY_TO_DEPLOY) or the
  exact CLI / IaC snippet to close each gap (PREREQUISITES_MISSING).
- NOTES with managed policy version, attach-vs-embed, and distribution
  deploy state caveats.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 1 Deploy specialist for CloudFront response headers).
- `/aws:deploy-cloudfront-distribution` for full distribution
  provisioning (origin, OAC, WAF, TLS, cache policy) — this response
  headers skill attaches to an existing distribution or runs alongside
  the distribution deployer.
- `/aws:audit-cloudfront-distribution` for post-deployment security
  auditing (TLS, OAC, WAF, headers posture).
