# Edge Compute and Response Headers Reference

Supplementary reference for the CloudFront Distribution Deployer skill.
Use when choosing between CloudFront Functions and Lambda@Edge, sizing
edge compute, configuring KeyValueStore, or building a response headers
policy for security headers.

## CloudFront Functions vs Lambda@Edge

| Dimension | CloudFront Functions | Lambda@Edge |
|---|---|---|
| Runtime | JavaScript (limited ES subset) | Node.js 18/20, Python 3.11 |
| Startup latency | Sub-millisecond | 50-500 ms cold start |
| Memory | 2 MB (code + KeyValueStore) | 128 MB - 3 GB |
| Execution time | < 1 ms typical, 5 ms max | Up to 5 sec (viewer), 30 sec (origin) |
| Network access | No | Yes |
| Filesystem | No | Read-only `/tmp` (viewer); full (origin) |
| Environment variables | No | Yes |
| Cost per million invocations | $0.10 | $0.60 + GB-second |
| Region constraint | Global (deployed to all edges) | MUST be created in us-east-1 |
| Triggers | viewer-request, viewer-response | viewer-request, viewer-response, origin-request, origin-response |

## When to use CloudFront Functions

- Header rewriting (add `X-Frame-Options: DENY` if origin doesn't send it)
- URL redirects (HTTP→HTTPS, www→apex, old path→new path)
- URL rewrites for SPA routing (`/*` → `/index.html`)
- JWT validation (signature verification only — no JWKS fetch)
- IP-based access control using KeyValueStore allowlist
- A/B test routing based on cookie or header
- Lightweight token normalization

## When to use Lambda@Edge

- External API calls (DynamoDB, Secrets Manager, third-party)
- Filesystem access (render template from `/tmp`)
- Complex transform requiring Python or full Node.js
- Database lookup for auth decision
- Image manipulation (origin-response trigger)
- JWT validation requiring JWKS fetch (network needed)
- Long-running logic (> 5 ms)

## KeyValueStore (KVS)

A serverless key-value store attached to a CloudFront Function. Allows
runtime data lookup without code redeploy.

**Use cases:**
- Feature flags (toggle behavior per-key)
- IP allowlist / blocklist (long lists without code bloat)
- Country-to-endpoint mapping
- A/B test cohort assignments
- Lightweight config (URL redirect maps)

**Limits:**
- 2 MB total (code + KVS data combined)
- Single KVS per function
- Updates propagate in minutes (eventual consistency)
- No transactions (key-level atomic only)

**Update KVS without redeploy:**
```bash
aws cloudfront keyvaluestore put-key \
  --kvs-arn arn:aws:cloudfront::<account>:key-value-store/<name> \
  --key "feature_xyz" --value "enabled"
```

The change propagates to all edge locations within minutes. The next
function invocation sees the new value.

## Response headers policy

A response headers policy controls which headers CloudFront adds, removes,
or overrides on the response to the viewer. Without an explicit policy,
CloudFront passes through whatever the origin sends.

**Security headers policy (recommended baseline):**
```json
{
  "ResponseHeadersPolicy": {
    "SecurityHeadersConfig": {
      "StrictTransportSecurity": {
        "AccessControlMaxAgeSec": 63072000,
        "IncludeSubdomains": true,
        "Preload": true,
        "Override": true
      },
      "FrameOptions": {"FrameOption": "DENY", "Override": true},
      "ContentTypeOptions": {"Override": true},
      "XSSProtection": {"Protection": true, "ModeBlock": true, "Override": true},
      "ReferrerPolicy": {"ReferrerPolicy": "strict-origin-when-cross-origin", "Override": true},
      "ContentSecurityPolicy": {
        "ContentSecurityPolicy": "default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'",
        "Override": true
      }
    }
  }
}
```

**HSTS preload eligibility:**
- max-age ≥ 31536000 (1 year); recommend 63072000 (2 years)
- includeSubdomains: true
- preload: true

Once the site is on the HSTS preload list, browsers refuse HTTP
connections to the domain. This is a strong posture but is hard to undo —
the preload list is browser-shipped and updates take months.

**CORS headers policy:**
```json
"CORSConfig": {
  "AccessControlAllowOrigins": {"Quantity": 1, "Items": ["https://app.example.com"]},
  "AccessControlAllowHeaders": {"Quantity": 3, "Items": ["Authorization", "Content-Type", "X-Requested-With"]},
  "AccessControlAllowMethods": {"Quantity": 4, "Items": ["GET", "POST", "PUT", "OPTIONS"]},
  "AccessControlAllowCredentials": true,
  "AccessControlMaxAgeSec": 600,
  "OriginOverride": true
}
```

## Server-Timing header

Enable to surface cache hit/miss and origin latency to the browser dev
tools. Useful for debugging cache behavior without CloudFront console
access. Disable in production for security (leaks cache topology).

```json
"ServerTimingHeadersConfig": {"Enabled": true, "SamplingRate": 0.1}
```

Sampling rate of 0.1 means 10% of responses include the header. Set to
1.0 for full visibility (debugging only).

## Custom headers (request to origin)

Origin custom headers are added by CloudFront to every request forwarded
to the origin. They do NOT appear in the viewer request.

**Common uses:**
- `X-Origin-Verify: <secret>` — origin validates this to confirm CloudFront
- `X-Forwarded-Host: example.com` — preserve viewer Host header
- `Authorization: Basic <token>` — origin auth (if origin can't be made public)

Custom headers with secrets are visible to anyone with read access to the
distribution config. Prefer IAM-based origin auth (ALB listener rule with
Cognito, Lambda authorizer) over static header secrets.
