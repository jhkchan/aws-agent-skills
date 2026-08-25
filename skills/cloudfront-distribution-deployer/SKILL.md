---
name: cloudfront-distribution-deployer
description: 'Provisions production-grade CloudFront distributions with secure defaults: Origin Access Control (OAC) for S3 origins (replaces legacy OAI), custom origin HTTPS with origin protocol policy, TLS 1.2 minimum with ACM certificates (must be in us-east-1), WAFv2 Web ACL association, managed cache and origin-request policies, origin group failover (active-active or active-passive), geo restriction allowlist/blocklist, Lambda@Edge vs CloudFront Functions selection, price class, S3 access logging, response headers policy for security headers, and latest features (KeyValueStore, continuous deployment staging). Emits a deployment plan with a READY_TO_DEPLOY checklist. Use when provisioning a new distribution, configuring OAC on S3 origins, attaching WAF at the edge, planning multi-origin failover, or hardening a CDN before production.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline architecture planning. Live deployment uses aws cloudfront create-distribution, create-origin-access-control, create-cache-policy, create-origin-request-policy, create-response-headers-policy, create-distribution-with-staging-config, aws wafv2 create-web-acl associate-web-acl, and aws acm list-certificates (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: experimental
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning a new CloudFront distribution for production, configuring Origin Access Control on S3 origins, attaching a WAFv2 Web ACL at the edge, planning multi-origin failover with origin groups, designing cache and origin request policies, setting up geo restriction, choosing between Lambda@Edge and CloudFront Functions, configuring security response headers, or planning a continuous-deployment (staging) distribution workflow.
  activation_triggers: create a CloudFront distribution, provision a CDN distribution, configure OAC on my S3 origin, CloudFront with WAF, multi-origin failover distribution, Lambda@Edge vs CloudFront Functions, CloudFront cache policy, CloudFront security headers, CloudFront geo restriction, CloudFront continuous deployment, ACM certificate for CloudFront, price class CloudFront
  invocation_schema: 'Input shape (one of): (a) a deployment specification including origin type (S3/custom/ALB), domain names, TLS requirements, WAF requirements, cache behavior requirements, geo restriction, edge compute requirements, logging destination, and price class; (b) a partial spec for interactive refinement (e.g., "CloudFront in front of an S3 bucket with OAC and WAF"); (c) an existing distribution ID for architecture review against the well-architected checklist. Output shape: { DISTRIBUTION_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING, ERROR }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudFront, distribution deploy, Origin Access Control, OAC, OAI migration, S3 origin, custom origin, ALB origin, OriginProtocolPolicy, ViewerProtocolPolicy, TLS 1.2, TLSv1.2_2021, ACM certificate, us-east-1, WAFv2, Web ACL, cache policy, origin request policy, managed policy, origin group, failover, geo restriction, Lambda@Edge, CloudFront Functions, KeyValueStore, price class, access logging, response headers policy, security headers, HSTS, continuous deployment, staging distribution, CDN provisioning
  tags: cloudfront, networking, deploy, cdn, oac, waf, tls, cache-policy, lambda-edge, cloudfront-functions, security-headers, geo-restriction
---

# CloudFront Distribution Deployer

## Mindset

**One-line takeaway:** a production CloudFront distribution is not "an
origin with a cache" — it is an **edge security stack** where every choice
(viewer protocol, origin protocol, TLS cipher policy, OAC vs OAI, WAF
association, security headers) is a deliberate defense-in-depth decision.
The cache hit ratio is the least interesting part; the **origin access
model, TLS posture, and WAF coverage** determine blast radius and exposure.

Three facts make CloudFront provisioning different from "point a domain
at a bucket":

- **OAC replaces OAI — and the bucket policy MUST change with it.** Origin
  Access Control (OAC) is the successor to Origin Access Identity (OAI).
  OAC supports SSE-KMS buckets (OAI does not — it cannot pass the KMS
  Decrypt permission), supports IPv6, and uses a service-principal bucket
  policy instead of a canonical-user grant. Migrating from OAI to OAC
  without updating the bucket policy breaks all object access (403). New
  distributions MUST use OAC; OAI is a migration-only legacy.

- **ACM certificates for CloudFront MUST live in us-east-1.** CloudFront
  is a global service, but it can only attach ACM certificates from the
  us-east-1 region. A cert in any other region fails distribution creation.
  This is an AWS hard constraint, not a recommendation. Operators in
  eu-west-1 or ap-southeast-1 routinely miss this — the cert exists, the
  region is wrong.

- **CloudFront Functions and Lambda@Edge are NOT interchangeable.**
  CloudFront Functions run in-edge (sub-millisecond startup, no network
  access, JavaScript-only, 2 MB code+KV). Lambda@Edge runs in regional
  edge caches (Node.js/Python, network access, longer cold starts, higher
  cost). Use Functions for lightweight request/response rewriting,
  header manipulation, URL redirects, and JWT validation. Use Lambda@Edge
  for anything requiring network calls, filesystem access, or >50 ms
  runtime. Picking the wrong one doubles cost or breaks the function.

## Quick reference — deployment checklist

| Dimension | Requirement | Step |
|---|---|---|
| Origin type | S3 REST (OAC), custom (ALB/EC2/on-prem HTTPS), or origin group | Step 1 |
| Origin Access Control | S3 REST origins MUST use OAC (signing behavior `always`) | Step 2 |
| Custom origin protocol | `https-only` for ALB/EC2/on-prem; never `http-only` or `match-viewer` | Step 3 |
| Viewer protocol | `redirect-to-https` (default) or `https-only` (strict) | Step 4 |
| TLS minimum | `TLSv1.2_2021` minimum (AEAD-only ciphers) | Step 5 |
| ACM certificate | In us-east-1, covers all alternate domain names | Step 5 |
| WAFv2 Web ACL | Associated, scope `CLOUDFRONT`, in us-east-1, with managed rule groups | Step 6 |
| Cache policy | Managed (e.g., `CachingOptimized`, `CachingDisabled`) or custom | Step 7 |
| Origin request policy | Managed (`AllViewerExceptHostHeader`, `AllViewer`) or custom | Step 7 |
| Response headers policy | Security headers: HSTS, X-Frame-Options, CSP, X-Content-Type-Options | Step 8 |
| Origin group | Active-active or active-passive failover for HA origins | Step 9 |
| Geo restriction | Allowlist or blocklist when regulatory/compliance requires | Step 10 |
| Price class | `PriceClass_100` (cheapest), `PriceClass_200`, `PriceClass_All` | Step 11 |
| Edge compute | CloudFront Functions (lightweight) or Lambda@Edge (complex) | Step 12 |
| Access logging | Standard logging to S3 with `awslogsdelivery` ACL grant | Step 13 |
| Continuous deployment | Staging distribution + traffic shifting for safe releases | Step 14 |

## Pre-flight: deployment specification gate (run before architecture output)

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment** — proceeding with an invalid
spec produces a non-functional or insecure distribution.

Live-account pre-flight checks (IAM create permissions, ACM cert ISSUED in us-east-1, S3 bucket region, custom-origin HTTPS reachability, WAF CLOUDFRONT scope) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load them before emitting the architecture plan for a live account.

| Attribute | Value | Effect on plan |
|---|---|---|
| Origin type | S3 REST (`bucket.s3.amazonaws.com`) | Configure OAC (Step 2). Bucket policy must be updated to service-principal. |
| Origin type | S3 website endpoint (`s3-website-*`) | **BLOCKER.** Forces public bucket — bypasses all S3 access policies. Switch to REST + OAC. |
| Origin type | Custom (ALB, EC2, on-prem) | Configure OriginProtocolPolicy (Step 3) and custom headers. |
| Origin type | Origin group (multi-origin) | Configure failover criteria (Step 9). |
| Domain names | Listed | MUST all be covered by the ACM certificate SAN. |
| WAF required | true | MUST be CLOUDFRONT scope, us-east-1. |
| Price class | `PriceClass_100` | North America + Europe edges only. Cheapest. |
| Price class | `PriceClass_All` | All edge locations (includes Asia, Africa, South America). |

**If the deployment spec is incomplete** (missing origin, viewer protocol
requirement, or domain name), output:

```text
DISTRIBUTION_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce a deployment plan without <field> — the resulting
distribution would be non-functional or insecure.
REQUIRED:
  - origin (S3 bucket name, ALB DNS, or origin group spec)
  - viewer_protocol_policy (redirect-to-https or https-only)
  - domain_names (alternate domain names; required for custom TLS cert)
  - tls_certificate (ACM ARN in us-east-1; or default cloudfront.net)
  - waf_association (true/false)
```

## Process — Architecture planning (apply in order, produce deployment plan)

### Step 0: Expert knowledge — non-obvious CloudFront behaviors that change the plan

Step 0 expert knowledge (TLSv1.2_2021 cipher policy, OAC signing behavior always vs no-override, bucket-policy pairing, us-east-1 WAF scope, Lambda@Edge replication, cache vs origin request policies, default behavior precedence, origin-group failover codes, price class vs latency, logging ACLs, staging distributions, response headers) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before finalizing the architecture plan.

### Step 1: Origin selection

| Origin type | When to use | Configuration |
|---|---|---|
| S3 REST | Static content, private bucket | `bucket.s3.<region>.amazonaws.com` + OAC |
| ALB | Dynamic application, multi-instance | ALB DNS + custom headers + `https-only` |
| EC2 / on-prem | Single-origin app, legacy | Origin DNS + custom headers + `https-only` |
| Origin group | HA across regions/datacenters | Primary + secondary + failover criteria |

**Anti-pattern:** NEVER use the S3 website endpoint
(`bucket.s3-website-<region>.amazonaws.com`) as an origin. It forces the
bucket to be publicly readable and bypasses S3 access policies entirely.
Use the REST endpoint with OAC instead.

### Step 2: Origin Access Control (S3 REST origins)

**Create the OAC:**
```bash
aws cloudfront create-origin-access-control \
  --origin-access-control-config \
  '{"Name":"oac-for-prod-bucket","Description":"OAC for prod S3 origin",
    "SigningProtocol":"sigv4","SigningBehavior":"always"}'
```

**Attach the OAC ID to the distribution's S3 origin:**
`OriginAccessControlId: <id-from-create>`

Step 2 OAC bucket-policy JSON (cloudfront.amazonaws.com principal with AWS:SourceArn) moved verbatim to [references/origin-access-control-guide.md](references/origin-access-control-guide.md).
Load on demand when writing the S3 bucket policy for the origin.

The bucket policy + OAC ID are deployed TOGETHER. OAC without the bucket
policy = 403. Bucket policy without OAC = inert (CloudFront has no signing).

### Step 3: Custom origin protocol policy (ALB / EC2 / on-prem)

| Value | Verdict | Notes |
|---|---|---|
| `https-only` | Required | CloudFront always connects over HTTPS. Verify origin has a valid cert. |
| `match-viewer` | NEVER | Propagates viewer protocol — if viewer used HTTP, origin traffic is HTTP. |
| `http-only` | NEVER | Plaintext origin traffic including custom headers (secrets). |

**Custom headers for origin secrets:** use `OriginCustomHeaders` to pass
shared secrets to the origin (e.g., `X-Origin-Verify: <token>`). The ALB
can verify this header to ensure traffic came from CloudFront.

**Origin SSL protocols:** set `OriginSslProtocols: ["TLSv1.2"]` minimum.
Do not include TLSv1 or TLSv1.1.

### Step 4: Viewer protocol policy

| Value | Recommendation | Notes |
|---|---|---|
| `redirect-to-https` | Default | Accepts HTTP request, returns 301 to HTTPS. The initial request URL (incl. query strings) travels over HTTP. |
| `https-only` | Strict environments | Rejects HTTP at the edge. Required when query strings carry tokens or PII. |
| `allow-all` | NEVER | Serves plaintext HTTP. Compliance violation (PCI-DSS 4.1, HIPAA 164.312(e)). |

### Step 5: TLS / SSL certificate and viewer TLS

**ACM certificate requirements:**
- **Region:** MUST be `us-east-1`. CloudFront is global but only reads ACM
  in us-east-1.
- **Status:** `ISSUED` (not `PENDING_VALIDATION`).
- **Subject Alternative Names (SAN):** MUST cover every domain in
  `Aliases` (alternate domain names). A cert for `www.example.com` cannot
  serve `api.example.com`.
- **Validation:** DNS validation recommended (auto-renews). Email
  validation expires.

**Viewer TLS minimum:**
```json
"ViewerCertificate": {
  "ACMCertificateArn": "arn:aws:acm:us-east-1:<account>:certificate/<id>",
  "SSLSupportMethod": "sni-only",
  "MinimumProtocolVersion": "TLSv1.2_2021",
  "CertificateSource": "acm"
}
```

SNI vs VIP guidance (legacy dedicated-IP viewers, $600/month) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a viewer cannot use SNI.

### Step 6: WAFv2 Web ACL association

Step 6 WAFv2 Web ACL CLI (create-web-acl, managed rule groups, association ARN) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when attaching the Web ACL (CLOUDFRONT scope, us-east-1).

### Step 7: Cache and origin request policies

**Use managed policies as starting points:**

| Managed policy | Use case |
|---|---|
| `CachingOptimized` | Static assets (images, CSS, JS) — maximize cache hit ratio |
| `CachingDisabled` | API responses, dynamic content — always go to origin |
| `CachingOptimizedForUncompressedCompressedObjects` | Static assets with compression |
| `Elemental-MediaPackage` | MediaPackage origins |
| `AllViewerExceptHostHeader` (origin request) | Forward everything except Host (origin determines Host) |
| `AllViewer` (origin request) | Forward all viewer info to origin |
| `CORS-CustomOrigin` (origin request) | CORS with custom origin |
| `UserAgentRefererHeaders` (cache) | Cache by User-Agent + Referer |

**Do NOT forward everything by default.** A cache policy that forwards
all headers/cookies/query strings produces a near-unique cache key per
request — cache hit ratio drops to near zero. Start with the most
restrictive managed policy that meets the use case, then add specific
headers as needed.

### Step 8: Response headers policy (security headers)

Step 8 security-headers policy JSON (HSTS, X-Frame-Options, CSP, X-Content-Type-Options) and HSTS rationale moved verbatim to [references/edge-compute-and-headers-guide.md](references/edge-compute-and-headers-guide.md).
Load on demand when building the response headers policy.

### Step 9: Origin group (multi-origin failover)

```json
"OriginGroups": {
  "Quantity": 1,
  "Items": [{
    "Id": "origin-group-ha",
    "Members": {"Quantity": 2, "Items": [
      {"OriginId": "primary-alb"},
      {"OriginId": "secondary-alb-dr"}
    ]},
    "FailoverCriteria": {
      "StatusCodes": {"Quantity": 6, "Items": [403, 404, 500, 502, 503, 504]}
    }
  }]
}
```

**Active-passive:** primary serves all traffic; secondary activates on
failure criteria. **Active-active:** not supported via origin group — use
Route 53 weighted routing or CloudFront continuous deployment.

### Step 10: Geo restriction

```json
"Restrictions": {
  "GeoRestriction": {
    "RestrictionType": "whitelist",
    "Items": ["US", "CA", "GB", "DE", "FR"]
  }
}
```

Use `whitelist` (allowlist) for compliance-bound workloads (e.g., GDPR
data residency). Use `blacklist` (blocklist) for OFAC-sanctioned
countries. A restriction of `none` is acceptable for globally-public
content (marketing sites, documentation).

### Step 11: Price class

| Price class | Coverage | Cost impact |
|---|---|---|
| `PriceClass_100` | US, Canada, Europe | Cheapest. Best for Western-hemisphere audiences. |
| `PriceClass_200` | Above + Middle East, Africa, Asia (excluding most expensive regions) | Mid. |
| `PriceClass_All` | All edge locations globally | Highest. Required for global audiences. |

### Step 12: Edge compute — CloudFront Functions vs Lambda@Edge

| Dimension | CloudFront Functions | Lambda@Edge |
|---|---|---|
| Runtime | JavaScript (limited) | Node.js, Python |
| Startup | Sub-millisecond | 50-500 ms cold start |
| Memory | 2 MB (code + KeyValueStore) | 128 MB - 3 GB |
| Network access | No | Yes |
| Filesystem | No | Read-only `/tmp` |
| Cost per invocation | ~1/10th of Lambda@Edge | Higher |
| Region constraint | Global | MUST be created in us-east-1 |
| Use cases | Header rewriting, URL redirects, JWT validation, KV lookups | External API calls, complex transforms, A/B testing |

**KeyValueStore (2024):** a serverless key-value store attached to a
CloudFront Function. Use for feature flags, lightweight config, IP
allowlists. Updates propagate in minutes — no function redeploy needed.

### Step 13: Access logging

**Standard logging (S3):**
```json
"Logging": {
  "Enabled": true,
  "IncludeCookies": true,
  "Bucket": "prod-cf-logs.s3.amazonaws.com",
  "Prefix": "cdn-logs/"
}
```

Step 13 logging-bucket ACL grant (awslogsdelivery canonical ID) and real-time logging config moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when enabling access logging.

### Step 14: Continuous deployment (staging distributions)

Step 14 continuous-deployment CLI (create-distribution-with-staging-config, copy-distribution) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when planning a staging distribution.

## Output format (per distribution deployment plan)

```text
DISTRIBUTION_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Origin: <S3 REST + OAC | ALB https-only | origin group failover>
  Viewer protocol: <redirect-to-https | https-only>
  TLS: <TLSv1.2_2021 + ACM cert ARN in us-east-1>
  WAF: <associated ARN | none>
  Cache policy: <managed policy name or custom>
  Origin request policy: <managed policy name or custom>
  Response headers: <security headers policy attached>
  Geo: <whitelist/blocklist/none>
  Price class: <100/200/All>
  Edge compute: <CloudFront Functions | Lambda@Edge | none>
  Logging: <S3 standard + ACL grant | real-time | none>
CHECKLIST:
  [x] Origin is S3 REST with OAC (or custom HTTPS)
  [x] OriginAccessControlId set on S3 origin
  [x] Bucket policy updated to service-principal with AWS:SourceArn
  [x] Custom origin protocol is https-only
  [x] ViewerProtocolPolicy is redirect-to-https or https-only
  [x] MinimumProtocolVersion is TLSv1.2_2021
  [x] ACM certificate is in us-east-1, covers all aliases
  [x] WAFv2 Web ACL associated (CLOUDFRONT scope, us-east-1)
  [x] Cache policy attached (managed or custom)
  [x] Response headers policy with HSTS/CSP/X-Frame-Options
  [x] Origin group failover criteria defined (if multi-origin)
  [x] Geo restriction set (whitelist/blocklist or explicit none)
  [x] Price class matches audience geography
  [x] Access logging enabled with ACL grant on logging bucket
FINDINGS:
  - [INFO] Estimated monthly cost: $0 base + $0.085/GB to origin + $0.02/GB to internet
  - [WARN] Geo restriction is none — content served globally without restriction
DEPLOY_COMMANDS:
  <ordered list of aws cloudfront create-* commands>
```

### Worked example — S3 origin with OAC + WAF + full security stack

```text
DISTRIBUTION_SPEC: prod-cdn-app
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Origin: S3 REST (prod-app-assets.s3.us-east-1.amazonaws.com) + OAC
  Viewer protocol: redirect-to-https
  TLS: TLSv1.2_2021 + ACM cert arn:aws:acm:us-east-1:111111111111:certificate/abc-123
  WAF: arn:aws:wafv2:us-east-1:111111111111:global/webacl/prod-cdn-waf/def-456
  Cache policy: CachingOptimized (static assets)
  Origin request policy: none (S3 origin, no forwarding needed)
  Response headers: security-headers-policy (HSTS 2yr, CSP, DENY frame)
  Geo: whitelist (US, CA, GB, DE, FR)
  Price class: PriceClass_100
  Edge compute: CloudFront Function (URL rewrite for SPA routing)
  Logging: S3 standard (prod-cf-logs.s3.amazonaws.com) + ACL grant
CHECKLIST:
  [x] Origin is S3 REST with OAC (signing behavior: always)
  [x] OriginAccessControlId set on S3 origin
  [x] Bucket policy updated to service-principal with AWS:SourceArn
  [x] Custom origin protocol: N/A (S3 origin)
  [x] ViewerProtocolPolicy: redirect-to-https
  [x] MinimumProtocolVersion: TLSv1.2_2021
  [x] ACM cert in us-east-1, covers app.example.com www.example.com
  [x] WAFv2 Web ACL associated (CommonRuleSet + SQLiRuleSet + rate-based)
  [x] Cache policy: CachingOptimized attached
  [x] Response headers policy: HSTS + CSP + X-Frame-Options DENY
  [x] Origin group: N/A (single origin)
  [x] Geo: whitelist US/CA/GB/DE/FR
  [x] Price class: 100
  [x] Access logging: enabled, ACL grant to awslogsdelivery
FINDINGS:
  - [INFO] Gateway Endpoints N/A — CloudFront does not use VPC endpoints
  - [INFO] Estimated monthly cost: $0 base + $0.085/GB to S3 + $0.02/GB to viewers
  - [NOTE] HSTS preload enabled — browsers will refuse HTTP for 2 years
DEPLOY_COMMANDS:
  1. aws cloudfront create-origin-access-control (signing behavior: always)
  2. aws s3api put-bucket-policy (service-principal with AWS:SourceArn condition)
  3. aws acm list-certificates --region us-east-1 (verify cert ISSUED)
  4. aws wafv2 create-web-acl --scope CLOUDFRONT --region us-east-1
  5. aws cloudfront create-cache-policy (if custom; else use managed)
  6. aws cloudfront create-response-headers-policy (security headers)
  7. aws cloudfront create-cloudfront-function (URL rewrite for SPA)
  8. aws cloudfront create-distribution (with all attached configs)
  9. aws cloudfront wait distribution-deployed
  10. aws wafv2 associate-web-acl (associate Web ACL with distribution ARN)
```

## Verification commands (run after deployment)

Post-deployment verification commands (distribution status, OAC, WAF association, ACM status, logging ACL, curl) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand after the distribution reaches Deployed.

## Edge-case handling

Edge-case catalog (ACM cert in wrong region, S3 website endpoint origin, self-signed origin cert, Lambda@Edge region, REGIONAL WAF scope, regulatory geo overlap) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when the spec hits a non-standard case.

## Anti-Patterns — NEVER

- NEVER use the S3 website endpoint as an origin. It forces the bucket to
  be publicly readable and bypasses all S3 access policies. Use the REST
  endpoint with OAC.

- NEVER deploy an S3 origin without OAC (or, for migration only, OAI).
  Without either, the bucket must be public — direct-origin bypass defeats
  WAF, geo restrictions, and signed URLs.

- NEVER set `MinimumProtocolVersion` below `TLSv1.2_2021`. The year suffix
  is the cipher policy, not the TLS version. `_2019` still permits CBC-mode
  ciphers; only `_2021` restricts to AEAD-only (GCM).

- NEVER use `OriginProtocolPolicy: match-viewer` or `http-only` for custom
  origins. `match-viewer` propagates the viewer's protocol (HTTP before
  redirect = HTTP to origin). `http-only` is plaintext origin traffic
  including custom headers with secrets.

- NEVER assume the bucket policy update is optional when migrating from
  OAI to OAC. OAC requires a service-principal statement
  (`Service: cloudfront.amazonaws.com` with `AWS:SourceArn` condition).
  OAI uses a `CanonicalUser` grant. They are not interchangeable — leaving
  the OAI policy in place after switching to OAC breaks all object access.

- NEVER create an ACM certificate outside us-east-1 for CloudFront.
  CloudFront is global but reads ACM only from us-east-1. This is an AWS
  hard constraint.

- NEVER associate a `REGIONAL`-scope WAFv2 Web ACL with a CloudFront
  distribution. Only `CLOUDFRONT`-scope ACLs work, and only in us-east-1.

- NEVER use `allow-all` for ViewerProtocolPolicy. It serves plaintext HTTP
  to viewers and is a PCI/HIPAA/SOC2 violation.

- NEVER create a Lambda@Edge function outside us-east-1. CloudFront cannot
  attach it.

- NEVER forward all viewer headers/cookies/query strings in a cache policy
  without considering cache hit ratio. Each unique combination produces a
  distinct cache entry. Start with the most restrictive managed policy.

- NEVER skip the response headers policy. CloudFront does not add HSTS,
  CSP, X-Frame-Options, or X-Content-Type-Options by default. Without an
  explicit policy, the distribution inherits whatever the origin sends —
  often nothing.

- NEVER enable continuous deployment and forget the promotion path. A
  staging distribution with no documented promotion procedure becomes
  drift. Always document: validate on staging at X% traffic, then
  `copy-distribution` to primary.

- NEVER assume standard logging works without the ACL grant. A logging
  bucket with ACLs disabled (BucketOwnerEnforced) silently rejects
  CloudFront logs. The grant to `awslogsdelivery` canonical ID is required.

## Pre-flight safety checks (run before any deployment CLI)

Pre-flight safety checks (CONFIRMATION GATE, ACM region check, WAF scope check, bucket-policy dry-run, cost estimate, global propagation) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load them before emitting any deployment CLI.

## Remediation guidance

Remediation guidance for PREREQUISITES_MISSING verdicts (ACM cert region, S3 website endpoint origin, Lambda@Edge region) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when writing the remediation steps.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert knowledge, Step 5 SNI/VIP, Step 6 WAF CLI, Step 13 logging grants, Step 14 staging CLI, edge-case catalog, and recent AWS features moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight checks, post-deployment verification commands, and pre-flight safety checks moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — remediation guidance for PREREQUISITES_MISSING moved from SKILL.md
- [references/origin-access-control-guide.md](references/origin-access-control-guide.md) — OAC vs OAI, signing behaviors, bucket policy patterns (now also holds the Step 2 bucket-policy JSON)
- [references/edge-compute-and-headers-guide.md](references/edge-compute-and-headers-guide.md) — Functions vs Lambda@Edge, KeyValueStore, response headers policies (now also holds the Step 8 security-headers JSON)

## Domain

AWS CloudOps / CloudFront Edge Security & Content Delivery Provisioning.

## Recent AWS features (2024-2026)

Recent AWS features 2024-2026 (KeyValueStore, continuous deployment, VPC origins, TLS 1.3, OAC for Lambda URLs/MediaStore, CloudFront Metrics) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when the spec mentions KVS, VPC origins, or staging workflows.

## AWS documentation

- **Amazon CloudFront Developer Guide** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html
- **CloudFront Security** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/security.html
- **Origin Access Control** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html
- **CloudFront Functions** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudfront-functions.html
- **Lambda@Edge** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html
- **CloudFront API Reference** — https://docs.aws.amazon.com/cloudfront/latest/APIReference/
- **CloudFront CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudfront/
- **WAFv2 Developer Guide** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html
- **Blog: KeyValueStore** — https://aws.amazon.com/blogs/networking-and-content-delivery/introducing-cloudfront-keyvaluestore/
- **Blog: Continuous deployment** — https://aws.amazon.com/blogs/networking-and-content-delivery/use-continuous-deployment-to-safely-deploy-cloudfront-distribution-changes/
