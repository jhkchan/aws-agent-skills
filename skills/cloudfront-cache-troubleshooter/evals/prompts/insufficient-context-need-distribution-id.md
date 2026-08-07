# Eval prompt: insufficient-context-need-distribution-id

Diagnose the following CloudFront caching report. The user has provided
only a vague symptom — no distribution ID, no domain, no curl headers, no
cache policy details. Emit the standard VERDICT block. If the diagnostic
tree cannot proceed without more evidence, emit NEED_MORE_INFO and list
the missing inputs.

## Scenario

A user reports: "CloudFront is not caching my content, the origin is
overloaded." They mention the application name `web-frontend` but do not
provide any further identifying information.

## What the user has provided

- Application name: `web-frontend`
- Symptom: "CloudFront is not caching, origin is overloaded"

## What the user has NOT provided

- The CloudFront distribution ID.
- The CloudFront domain name (e.g., `d123.cloudfront.net`).
- The `curl -I` response headers from CloudFront (no `x-cache`,
  `Age`, or `Cache-Control` values).
- The `curl -I` response headers from the origin (no origin
  `Cache-Control` header to evaluate).
- The cache policy ID or its TTL/header/cookie/query-string settings.
- Whether Lambda@Edge functions or WAF are attached.
- The CloudFront access log data (`x-edge-result-type` distribution).
- The origin type (S3, ALB, on-prem).
- Whether this is a new issue or has always been the case.
- Whether a recent deployment or config change coincides with the issue.
