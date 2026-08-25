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

**Live-account pre-flight checks (skip if doing offline architecture plan):**
1. Verify IAM permissions for `cloudfront:CreateDistribution`,
   `cloudfront:CreateOriginAccessControl`, `cloudfront:CreateCachePolicy`,
   `cloudfront:CreateOriginRequestPolicy`, `cloudfront:CreateResponseHeadersPolicy`,
   `cloudfront:CreateDistributionWithStagingConfig`, and
   `wafv2:CreateWebACL`, `wafv2:AssociateWebACL`.
2. Verify the ACM certificate exists and is ISSUED in us-east-1:
   `aws acm list-certificates --region us-east-1 --output text`
3. For S3 origins, verify the bucket exists and note its region
   (cross-region S3 origins are supported but incur cross-region data
   transfer to the CloudFront edge).
4. For ALB/EC2 custom origins, verify HTTPS is reachable on 443 and the
   origin certificate is trusted by CloudFront (public CA, not self-signed).
5. For WAFv2, verify the Web ACL scope is `CLOUDFRONT` (not `REGIONAL`).

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

- **TLSv1.2_2021 vs TLSv1.2_2019 is a cipher-suite difference.** Both
  negotiate TLS 1.2+, but `_2021` removes all CBC-mode ciphers (keeps AEAD
  only). `_2019` still permits `ECDHE-RSA-AES128-SHA256` (CBC) which is
  vulnerable to padding-oracle variants. Always set `MinimumProtocolVersion:
  TLSv1.2_2021` for new distributions.

- **OAC signing behavior `always` vs `no-override`.** `always` signs every
  origin request (recommended for private S3). `no-override` signs only if
  no `Authorization` header is present (use when the origin also accepts
  its own auth). For S3 REST origins serving static content, use `always`.

- **OAC does NOT replace the bucket policy.** OAC is the CloudFront-side
  configuration. The S3 bucket must STILL grant `s3:GetObject` to
  `Service: cloudfront.amazonaws.com` with the
  `AWS:SourceArn` condition matching the distribution ARN. Without the
  bucket policy update, every object GET returns 403.

- **WAFv2 Web ACL for CloudFront MUST be in us-east-1 with CLOUDFRONT scope.**
  `aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1` is the
  only way to enumerate them. A Web ACL in eu-west-1, even with CLOUDFRONT
  scope, cannot be associated.

- **Lambda@Edge functions MUST be in us-east-1 (and replicated).** You
  create the Lambda function in us-east-1; CloudFront replicates it to
  regional edge caches worldwide. A function created in any other region
  cannot be attached to a distribution.

- **CloudFront Functions are region-less (global).** They are deployed
  directly to all edge locations. No region constraint.

- **Cache policy and origin request policy are SEPARATE.** Cache policy
  controls which headers/cookies/query strings CloudFront caches
  (determines cache key). Origin request policy controls which
  headers/cookies/query strings CloudFront forwards to the origin
  (determines what the origin sees). Use managed policies as starting
  points; do not blindly forward everything (kills cache hit ratio).

- **Default cache behavior applies to unmatched paths.** Path-specific
  cache behaviors override for matched patterns (`/api/*`, `*.jpg`). Always
  configure the default behavior with the broadest applicable policy.

- **Origin group failover triggers on HTTP status codes.** Configure the
  failover criteria (e.g., 403, 404, 500, 502, 503, 504). The primary is
  tried first; on a matching status code, CloudFront switches to the
  secondary. Active-active requires a different setup (weighted routing at
  Route 53).

- **Price class controls cost but also latency.** `PriceClass_100` uses
  only North America + Europe edges — Asian users see higher latency.
  `PriceClass_All` includes all 600+ edge locations but has a higher
  per-GB rate in some regions.

- **Standard logging uses ACLs (not bucket policies).** The logging S3
  bucket must grant WRITE and READ_ACP to the `awslogsdelivery` account
  canonical ID (`c4c1ede66af53448b93ce283fc5b7c73`). A bucket with ACLs
  disabled (BucketOwnerEnforced) silently rejects logs. For new deployments,
  prefer real-time logging (`RealtimeLogConfigArn`) over standard logging.

- **Continuous deployment (staging distributions) requires a primary.**
  You create a staging distribution that mirrors the primary and shifts a
  percentage of traffic. After validation, you promote the staging config
  to the primary. The primary must exist first.

- **Response headers policy is REQUIRED for security headers.** Without an
  explicit policy, CloudFront passes through whatever the origin sends. If
  the origin does not send HSTS, CSP, or X-Frame-Options, the edge does
  not add them.

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

**Update the S3 bucket policy to grant CloudFront access via OAC:**
```json
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "cloudfront.amazonaws.com"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::prod-bucket/*",
    "Condition": {
      "StringEquals": {
        "AWS:SourceArn": "arn:aws:cloudfront::<account>:distribution/<dist-id>"
      }
    }
  }]
}
```

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

**SNI vs VIP:** `sni-only` is the modern default (requires SNI-capable
client — all modern browsers). `vip` is legacy, costs $600/month, reserved
for ancient clients (Java 6, Windows XP). Use SNI unless you have a
specific SNI-incompatible client.

### Step 6: WAFv2 Web ACL association

**Create the Web ACL (CLOUDFRONT scope, us-east-1):**
```bash
aws wafv2 create-web-acl \
  --name prod-cdn-waf --scope CLOUDFRONT --region us-east-1 \
  --default-action Allow={} \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=prod-cdn-waf \
  --rules file://waf-rules.json
```

**Recommended rule groups:**
- `AWSManagedRulesCommonRuleSet` — OWASP Top 10 baseline.
- `AWSManagedRulesSQLiRuleSet` — SQL injection patterns.
- `AWSManagedRulesAmazonIpReputationList` — known malicious IPs.
- `AWSManagedRulesBotControlRuleSet` — bot/scraper detection.
- Rate-based rule — e.g., 2000 requests per 5 minutes per IP.

**Associate with the distribution:**
Set `WebACLId` in the distribution config to the Web ACL ARN
(`arn:aws:wafv2:us-east-1:<account>:global/webacl/<name>/<id>`).

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

**Required security headers:**
```json
"ResponseHeadersPolicy": {
  "SecurityHeadersConfig": {
    "StrictTransportSecurity": {"AccessControlMaxAgeSec": 63072000, "IncludeSubdomains": true, "Override": true, "Preload": true},
    "FrameOptions": {"FrameOption": "DENY", "Override": true},
    "ContentTypeOptions": {"Override": true},
    "XSSProtection": {"Protection": true, "ModeBlock": true, "Override": true},
    "ReferrerPolicy": {"ReferrerPolicy": "strict-origin-when-cross-origin", "Override": true},
    "ContentSecurityPolicy": {"ContentSecurityPolicy": "default-src 'self'; object-src 'none'", "Override": true}
  }
}
```

HSTS at max-age 63072000 (2 years) with preload signals to browsers: never
connect to this site over HTTP. This is the strongest transport-security
posture available at the edge.

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

**Logging bucket ACL grant (REQUIRED):**
```bash
aws s3api put-object-acl --bucket prod-cf-logs --key cdn-logs/ \
  --grant-write 'id="c4c1ede66af53448b93ce283fc5b7c73"' \
  --grant-read-acp 'id="c4c1ede66af53448b93ce283fc5b7c73"'
```
(The canonical ID `c4c1ede66af53448b93ce283fc5b7c73` is the
`awslogsdelivery` account.)

**Real-time logging (newer, recommended for production):**
```json
"RealtimeLogConfigArn": "arn:aws:cloudfront::<account>:realtime-log-config/prod-cf-rt"
```
Real-time logs stream to Kinesis Data Firehose (S3, OpenSearch, etc.)
within seconds. Better for anomaly detection than the 5-60 minute delay
of standard logging.

### Step 14: Continuous deployment (staging distributions)

```bash
aws cloudfront create-distribution-with-staging-config \
  --staging-config-comment "staging for prod-cdn" \
  --default-cache-behavior ...
# After validation:
aws cloudfront copy-distribution --if-match <etag> --staging-distribution-id <id> --primary-distribution-id <id>
```

Use staging distributions to test config changes (new origins, new WAF
rules, new cache policies) with a small percentage of traffic before
promoting to the primary. Eliminates "deploy and pray" CDN releases.

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

```bash
# Verify distribution is Deployed
aws cloudfront get-distribution --id <id> \
  --query 'Distribution.Status'

# Verify OAC exists
aws cloudfront get-origin-access-control --id <oac-id>

# Verify WAF is associated
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.WebACLId'

# Verify ACM cert is in us-east-1 and ISSUED
aws acm describe-certificate --certificate-arn <arn> --region us-east-1 \
  --query 'Certificate.Status'

# Verify logging bucket ACL grant
aws s3api get-object-acl --bucket prod-cf-logs --key cdn-logs/

# Test distribution
curl -I https://<distribution-domain>.cloudfront.net/
# Expect: HTTP/2 200, strict-transport-security header present
```

## Edge-case handling

- **ACM certificate in wrong region.** PREREQUISITES_MISSING. CloudFront
  can only read ACM certificates from us-east-1. Re-issue the cert in
  us-east-1 or use the default `*.cloudfront.net` domain.

- **S3 website endpoint origin.** PREREQUISITES_MISSING. Switch to REST
  endpoint + OAC. The website endpoint forces a public bucket and bypasses
  S3 access policies.

- **Self-signed origin certificate.** PREREQUECISITES_MISSING. CloudFront
  does not trust self-signed certs. Use ACM (for ALB) or a public CA cert.

- **Lambda@Edge function in non-us-east-1.** PREREQUISITES_MISSING. Move
  the function to us-east-1.

- **WAFv2 Web ACL with REGIONAL scope.** PREREQUISITES_MISSING. Re-create
  with `--scope CLOUDFRONT` in us-east-1.

- **Geo restriction with regulatory overlap.** If the workload is subject
  to multiple regimes (GDPR + OFAC), use a whitelist of explicitly-allowed
  countries. A blacklist of disallowed countries is harder to maintain.

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

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-distribution`, `update-distribution`, `create-origin-access-control`),
  the deployer MUST emit:
  `CONFIRM: About to deploy distribution <name> in account <account>.
  Estimated monthly cost: <$X>. Distribution changes propagate globally
  (5-60 min). Proceed? (yes/no)`

- **ACM cert region check.** `aws acm describe-certificate --certificate-arn
  <arn> --region us-east-1 --query 'Certificate.Status'` MUST return
  `ISSUED`. A cert in any other region or in `PENDING_VALIDATION` fails.

- **WAF scope check.** `aws wafv2 list-web-acls --scope CLOUDFRONT --region
  us-east-1` MUST list the intended ACL. REGIONAL-scope ACLs cannot be
  associated.

- **S3 bucket policy dry-run.** Before attaching OAC, verify the bucket
  policy has the service-principal statement. Without it, all object GETs
  fail immediately on distribution deployment.

- **Cost estimate.** Emit before deployment:
  - CloudFront data transfer to origin: $0.085/GB (varies by price class)
  - CloudFront data transfer to internet: $0.02/GB (varies by region)
  - Lambda@Edge invocations: $0.60 per million + GB-second
  - CloudFront Functions: $0.10 per million
  - WAF: $5/ACL/month + $0.60 per million requests
  - Real-time logging: Kinesis cost

- **Distribution update is global.** Changes take 5-60 minutes to propagate
  to all edge locations. Verify via `get-distribution Status: Deployed`
  before declaring deployment complete.

## Remediation guidance

**Ordering principle:** origin access model first (active exposure if wrong),
then TLS posture (data-in-transit), then WAF (defense-in-depth), then
optimizations (caching, headers).

### For PREREQUISITES_MISSING — ACM cert in wrong region

1. Re-issue or import the cert in us-east-1:
   `aws acm request-certificate --domain-name app.example.com --validation-method DNS --region us-east-1`
2. Wait for `ISSUED` status.
3. Update distribution config with the new ARN.

### For PREREQUISITES_MISSING — S3 website endpoint origin

1. Switch origin to REST endpoint: `bucket.s3.<region>.amazonaws.com`.
2. Create OAC and attach to the origin.
3. Update bucket policy to service-principal with `AWS:SourceArn`.
4. Remove public read access from the bucket.

### For PREREQUISITES_MISSING — Lambda@Edge in wrong region

1. Recreate the function in us-east-1.
2. Publish version: `aws lambda publish-version --function-name <name> --region us-east-1`.
3. Update distribution to reference the new function ARN with version suffix.

## Domain

AWS CloudOps / CloudFront Edge Security & Content Delivery Provisioning.

## Recent AWS features (2024-2026)

- **KeyValueStore (2024):** serverless key-value data for CloudFront
  Functions. Use for feature flags, lightweight config, IP allowlists.
  Updates propagate in minutes without function redeploy.

- **Continuous deployment (2024):** staging distributions with
  percentage-based traffic shifting. Promote staging config to primary
  after validation. Eliminates risky CDN releases.

- **VPC origins (2024-2025):** CloudFront can origin from private VPC
  resources (ALB, NLB, EC2, ECS) without internet exposure. Useful for
  internal-only applications needing edge delivery.

- **TLS 1.3 viewer support (2024):** CloudFront supports TLS 1.3 for
  viewer connections. Set `MinimumProtocolVersion: TLSv1.2_2021` as the
  floor; clients negotiate 1.3 if capable.

- **Origin Access Control for Lambda Function URLs and MediaStore
  (2024-2025):** OAC now covers more than S3. Verify OAC on all origin
  types when auditing.

- **CloudFront Metrics (2025):** Enhanced real-time metrics in CloudWatch
  plus additional edge-side dimensions for debugging cache hit ratios.

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
