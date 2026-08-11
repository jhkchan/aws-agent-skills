---
name: cloudfront-response-headers-deployer
description: >-
  Provisions CloudFront response headers policies with secure defaults: security
  headers (Content-Security-Policy, Strict-Transport-Security, X-Frame-Options,
  X-Content-Type-Options, Referrer-Policy, Permissions-Policy), CORS
  configuration (access-control-allow-origin, methods, headers, credentials,
  expose-headers, max-age, preflight), custom headers (Cache-Control, X-Custom),
  removal headers (Server, X-Powered-By), managed policies
  (CORS-with-preflight-and-SecurityHeadersPolicy, SimpleCORS,
  CORSAndHTTPSecurityHeadersPolicy, SecurityHeadersPolicy), and the latest
  CloudFront response headers policy managed updates. Emits a deployment plan
  with a verdict (READY_TO_DEPLOY with full CloudFormation / Terraform template
  | PREREQUISITES_MISSING with specific gap and remediation). Use when
  provisioning security headers on a CloudFront distribution, configuring CORS
  for cross-origin access, attaching managed SecurityHeadersPolicy, removing
  server fingerprint headers, or hardening a CDN's HTTP response posture.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws cloudfront create-response-headers-policy,
  get-response-headers-policy, update-response-headers-policy,
  delete-response-headers-policy, list-response-headers-policies,
  create-response-headers-policy-config, get-distribution-config,
  update-distribution, create-distribution, list-conflicting-aliases, and
  aws cloudfront get-cache-policy-config (AWS CLI v2, SSO or key-based
  credentials).
keywords:
  - CloudFront
  - response headers policy
  - security headers
  - Content-Security-Policy
  - CSP
  - Strict-Transport-Security
  - HSTS
  - X-Frame-Options
  - X-Content-Type-Options
  - Referrer-Policy
  - Permissions-Policy
  - CORS
  - access-control-allow-origin
  - preflight
  - managed policy
  - SecurityHeadersPolicy
  - SimpleCORS
  - Cache-Control
  - custom headers
  - removal headers
  - Server header
  - X-Powered-By
tags:
  - cloudfront
  - networking
  - deploy
  - security-headers
  - cors
  - response-headers-policy
  - cdn
  - hardening
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Provisioning a CloudFront response headers policy for security headers
    (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy,
    Permissions-Policy); configuring CORS for cross-origin access (simple CORS,
    preflight, credentials); attaching a managed policy
    (SecurityHeadersPolicy, CORSAndHTTPSecurityHeadersPolicy,
    SimpleCORS, CORS-with-preflight-and-SecurityHeadersPolicy); removing
    server fingerprint headers (Server, X-Powered-By); setting custom headers
    (Cache-Control, X-Custom); or hardening a distribution's HTTP response
    posture before production.
  activation_triggers:
    - "create CloudFront response headers policy"
    - "CloudFront security headers"
    - "CloudFront CSP"
    - "CloudFront HSTS"
    - "CloudFront X-Frame-Options"
    - "CloudFront CORS"
    - "CloudFront access-control-allow-origin"
    - "CloudFront preflight"
    - "CloudFront managed SecurityHeadersPolicy"
    - "CloudFront SimpleCORS"
    - "CloudFront remove Server header"
    - "CloudFront remove X-Powered-By"
    - "CloudFront Cache-Control header"
    - "CloudFront Permissions-Policy"
    - "CloudFront Referrer-Policy"
    - "attach response headers policy to distribution"
  invocation_schema: >-
    Input shape (one of): (a) a deployment spec describing header requirements
    (security headers + values, CORS origin/methods/headers, custom headers,
    removal headers, managed vs custom policy); (b) a partial spec for
    interactive refinement ("security headers on my distribution"); (c) an
    existing distribution ID for policy review against the secure-defaults
    checklist. Output shape: { POLICY_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[],
    FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY,
    PREREQUISITES_MISSING }.
---

# CloudFront Response Headers Deployer

## What this skill does

Provisions CloudFront response headers policies with secure defaults —
security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options,
Referrer-Policy, Permissions-Policy), CORS configuration (origins,
methods, headers, credentials, preflight), custom headers (Cache-Control,
X-Custom), and removal headers (Server, X-Powered-By). Picks between
managed policies (`SecurityHeadersPolicy`, `CORSAndHTTPSecurityHeadersPolicy`,
`SimpleCORS`, `CORS-with-preflight-and-SecurityHeadersPolicy`) and custom
policies based on the operator's requirements. Runs deterministic
requirement checks before emitting the template — if all checks pass, the
verdict is `READY_TO_DEPLOY` with the populated CloudFormation / Terraform
template and the distribution update plan. If a requirement is missing
(no distribution to attach, conflicting managed policy reference, custom
origin not reachable), the verdict is `PREREQUISITES_MISSING` with the
specific gap and the exact CLI / IaC snippet that closes it.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + requirement checklist + capability matrix | Before any build |
| **§ Mindset** | Why response headers policies, the attach-vs-embed distinction, managed vs custom | Understanding the design model |
| **§ Pre-flight** | Requirement gate — distribution exists, origin reachable, cache policy compatibility | Before emitting any template |
| **§ Process** | Per-header design: security, CORS, custom, removal, managed | When designing each layer |
| **§ STRICT output contract** | Required labels + FORBIDDEN patterns + self-check | Before emitting any block |
| **§ Expert heuristic** | The 5 non-obvious failure modes that miss naive header setups | Defense-in-depth |
| **§ Anti-Patterns** | NEVER list — common mistakes that silently break headers | Review before emitting |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `READY_TO_DEPLOY` | All requirements satisfied (distribution exists or will be created alongside, origin reachable, no conflicting policy reference, managed policy ARN valid if used, CORS origin list consistent with cert SAN). Template generated. | Emit complete response headers policy template + distribution update plan |
| `PREREQUISITES_MISSING` | One or more requirements missing (distribution does not exist; managed policy does not exist in this account/region; CORS origin uses `*` with `AllowCredentials: true`; CSP conflicts with inline scripts; origin not reachable). | Emit the specific gap and the exact CLI / IaC snippet to close it. Hold the partial template as a draft. |

**Requirement checklist (all must be satisfied for READY_TO_DEPLOY):**

1. **Target distribution** — exists (for attach-to-existing) or will be
   created alongside the policy (for greenfield). Verify via
   `aws cloudfront get-distribution-config --id <id>`.
2. **Cache behavior target** — `DefaultCacheBehavior` or a specific
   `CacheBehavior` (matched by `PathPattern`). The policy attaches at
   the behavior level, not the distribution level.
3. **Origin reachable** — for CORS with credentials, the origin must be
   HTTPS (not HTTP). CloudFront rejects `Access-Control-Allow-Origin: *`
   combined with `Access-Control-Allow-Credentials: true`.
4. **Managed policy ARN** (if used) — `SecurityHeadersPolicy`,
   `CORSAndHTTPSecurityHeadersPolicy`, `SimpleCORS`, or
   `CORS-with-preflight-and-SecurityHeadersPolicy` exist as AWS-managed
   policies with fixed IDs (`0857826db9cffff310d5ad62955c9c26` etc.).
5. **CORS origin list** — specific origins or `*`. If `*`, the policy
   MUST NOT set `Access-ControlAllowCredentials: true` (browser rejects).
6. **CSP compatibility** — if CSP includes `script-src 'self'`, no
   inline `<script>` tags are allowed on the origin. If the site uses
   inline scripts, CSP must include `'unsafe-inline'` or nonces.
7. **HSTS includesubdomains** — must match the actual domain scope. If
   subdomains are served by a different CDN, `IncludeSubDomains` will
   pin them to HTTPS irreversibly for the HSTS duration.
8. **Removal header list** — `Server`, `X-Powered-By`, and any custom
   fingerprint headers. CloudFront adds its own `Server: CloudFront`
   and `Via` headers — these cannot be removed.
9. **Distribution state** — must be `Deployed` to attach a policy. A
   distribution in `InProgress` state rejects updates.
10. **Cache policy compatibility** — response headers policies are
    orthogonal to cache policies (one controls what CloudFront sends to
    viewers; the other controls what CloudFront caches from origins).
    No conflict possible, but the operator should know both are set.

**Capability matrix (which AWS service handles each layer):**

| Layer | Service | Common pitfalls |
|---|---|---|
| Security headers | CloudFront response headers policy | CSP too strict breaks site; HSTS too long is irreversible |
| CORS | CloudFront response headers policy | `*` + credentials = browser reject; preflight missing |
| Custom headers | CloudFront response headers policy | Cannot override `Server`, `Via` (CloudFront-injected) |
| Removal headers | CloudFront response headers policy | Removal list MUST match exact header names (case-sensitive) |
| Managed policies | AWS-managed, fixed IDs | Cannot modify; fork to custom if extension needed |
| Attachment | Distribution cache behavior | Policy attaches at behavior level; distribution update required |

## Mindset

**One-line takeaway:** a response headers policy is the only CloudFront
configuration surface that lets you add, modify, or remove HTTP response
headers without writing Lambda@Edge or CloudFront Functions. It is a
managed feature (no compute, no cost beyond the policy object storage).
Driven by three realities:

- **Response headers policies replaced the old "use Lambda@Edge to
  inject headers" pattern.** Before this feature, the only way to add
  `Content-Security-Policy` or `Strict-Transport-Security` was a
  Lambda@Edge function on the `viewer-response` event. Lambda@Edge
  costs money per invocation, has cold-start latency, and is a
  JavaScript ops surface. Response headers policies are free, instant,
  and declarative.

- **`Access-Control-Allow-Origin: *` with `AllowCredentials: true` is
  silently rejected by browsers.** CloudFront will happily emit the
  headers — the browser console shows the CORS error. The fix is a
  specific origin list when credentials are involved, OR an origin
  reflection pattern (echo back the requesting `Origin` header). The
  policy API does not validate this combination — the skill does.

- **Managed policies have fixed IDs that do NOT change by region.**
  `SecurityHeadersPolicy` is always `0857826db9cffff310d5ad62955c9c26`
  in every account, every region. This is unusual for AWS — most
  managed resources have account-specific ARNs. The implication: you
  can hard-code the managed policy ID in templates safely.

## Pre-flight: requirement gate

Run before emitting any template. Missing requirements produce
PREREQUISITES_MISSING with the exact gap.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws cloudfront get-distribution-config --id <id>` — confirm the
   target distribution exists and is in `Deployed` state.
2. `aws cloudfront list-response-headers-policies` — verify whether a
   policy with the target name already exists (create vs. update).
3. `aws cloudfront get-response-headers-policy --id <id>` — if updating,
   snapshot the existing config.
4. For CORS: verify the origin is reachable on HTTPS
   (`curl -I https://origin.example.com`). HTTP origins cannot serve
   credentialed CORS.
5. `aws cloudfront list-cache-policies` — verify the cache policy on
   the target behavior does not already inject conflicting headers.
6. For managed policy references: verify the managed policy ID is
   correct (`0857826db9cffff310d5ad62955c9c26` for `SecurityHeadersPolicy`).

**Malformed input:** if the input scenario is missing required fields
(distribution ID or "create new", target behavior, header requirements),
emit `VERDICT: PREREQUISITES_MISSING` with `GAP: Scenario missing
required field <field>. Provide <field> to proceed.`

| Requirement | Effect on automation |
|---|---|
| Distribution does not exist | PREREQUISITES_MISSING — emit `create-distribution` snippet or operator confirms "create alongside". |
| Distribution state is `InProgress` | PREREQUISITES_MISSING — wait for deployment; emit wait-and-retry note. |
| Policy name already exists | AUTOMATED (the template updates in place; emit CONFIRM gate). |
| CORS `*` with credentials | PREREQUISITES_MISSING — emit specific-origin-list or disable-credentials snippet. |
| CSP conflicts with known site scripts | PREREQUISITES_MISSING — emit CSP with `'unsafe-inline'` or nonce-based snippet. |
| HSTS IncludeSubDomains with subdomains on different CDN | PREREQUISITES_MISSING — emit HSTS without IncludeSubDomains snippet. |
| Origin not reachable on HTTPS | PREREQUISITES_MISSING — emit HTTPS enablement snippet. |
| Managed policy ID malformed | PREREQUISITES_MISSING — emit correct managed policy ID. |

## Process — response headers policy design (apply in order)

### Step 0: Expert knowledge — non-obvious CloudFront header behaviors

- **Response headers policies are versioned and immutable.** Each
  update creates a new `ETag`. The `get-response-headers-policy` returns
  the current ETag; `update-response-headers-policy` requires the
  current ETag to detect lost updates. Always snapshot via `get` before
  `update`.

- **The `Server` and `Via` headers CANNOT be removed.** CloudFront
  injects these at the edge. The `RemoveHeadersConfig` list silently
  ignores them. If you need to hide CloudFront, use a custom origin
  (not S3) and accept the fingerprint — there is no workaround.

- **CSP `default-src 'none'` is the most secure baseline.** Every
  resource type the site needs must be explicitly allowed. If the site
  loads images, add `img-src 'self'`. If it makes XHR, add
  `connect-src 'self'`. Starting from `'none'` and adding what's needed
  is the safest path.

- **`X-Frame-Options: DENY` and `frame-ancestors 'none'` in CSP are
  redundant.** Modern browsers that support CSP `frame-ancestors`
  ignore `X-Frame-Options`. Keep both for defense-in-depth (old
  browsers), but know that `frame-ancestors` wins in modern browsers.

- **`Strict-Transport-Security: max-age=63072000; includeSubDomains;
  preload` is the most aggressive HSTS config.** Once a browser sees
  this, ALL subdomains are HTTPS-only for 2 years. If a subdomain is
  served over HTTP (e.g., a legacy internal tool), it breaks. Use
  `max-age=300` initially to test, then increase.

- **CORS preflight (`OPTIONS`) requests are NOT cached by default.**
  The `Access-Control-Max-Age` header tells the browser how long to
  cache the preflight response. Set it to at least 86400 (1 day) to
  avoid redundant preflight round-trips.

- **`Access-Control-Allow-Credentials: true` requires a specific
  origin.** `Access-Control-Allow-Origin: *` is rejected by browsers
  when credentials are involved. Use a specific origin
  (`https://app.example.com`) or implement origin reflection.

- **Custom headers OVERRIDE origin headers.** If the origin emits
  `Cache-Control: no-cache` and the policy sets
  `Cache-Control: max-age=3600`, the policy value wins. Use this to
  normalize heterogeneous origin behavior.

- **Managed policies are versioned and updated by AWS.** AWS has
  updated `SecurityHeadersPolicy` historically (e.g., to add
  `Permissions-Policy` when the spec stabilized). Using a managed
  policy means your security posture improves automatically — but
  also means a change could break a site that relied on the old
  headers. Test after AWS announcements.

- **Response headers policies are NOT applied to error responses from
  the cache.** If CloudFront returns a cached 403 or 404, the response
  headers policy is NOT applied — only origin-sourced responses get
  the headers. To add headers to cached errors, use a custom error
  response with a managed error page.

- **The policy attaches to a cache behavior, not the distribution.**
  A distribution with multiple cache behaviors (e.g., `/api/*` vs
  `/static/*`) can have different response headers policies on each.
  The `DefaultCacheBehavior` is the catch-all.

- **`Permissions-Policy` (formerly Feature-Policy) is the modern way
  to disable browser features.** Use it to deny camera, microphone,
  geolocation, payment APIs at the CDN layer. Syntax:
  `camera=(), microphone=(), geolocation=()`.

### Step 1: Security headers design

| Header | Recommended value | Why |
|---|---|---|
| `Content-Security-Policy` | `default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'` | Mitigates XSS, clickjacking, data injection |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` (production); `max-age=300` (testing) | Forces HTTPS, prevents SSL stripping |
| `X-Frame-Options` | `DENY` (or `SAMEORIGIN` if iframes needed) | Clickjacking defense (legacy browsers) |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limits referrer leakage to cross-origin |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=()` | Disables browser feature APIs |

### Step 2: CORS configuration design

| Decision | Default | Why |
|---|---|---|
| `AllowOrigin` | specific origins (NOT `*` for credentialed) | `*` + credentials = browser reject |
| `AllowMethods` | `["GET", "HEAD", "OPTIONS"]` (read-only); add `POST, PUT, DELETE` for write APIs | Least-privilege |
| `AllowHeaders` | `["Authorization", "Content-Type"]` | Headers the browser is allowed to send |
| `ExposeHeaders` | `[]` (add `X-Total-Count` etc. for pagination) | Headers the browser JS can read |
| `AllowCredentials` | `false` (set `true` only for cookie-bearing requests) | Credentials + `*` origin is invalid |
| `MaxAgeSec` | `86400` (1 day) | Browser preflight cache duration |

**Origin reflection pattern** (echo back the requesting Origin header)
is NOT supported by response headers policies — use Lambda@Edge or
CloudFront Functions for origin reflection.

### Step 3: Custom headers design

| Use case | Header | Value |
|---|---|---|
| Force browser caching | `Cache-Control` | `public, max-age=3600` |
| Disable browser caching | `Cache-Control` | `no-store` |
| Sensitivity label | `X-Content-Classification` | `Restricted` |
| Service version | `X-Service-Version` | `1.2.3` |

Custom headers OVERRIDE origin-emitted headers with the same name.

### Step 4: Removal headers design

| Header | Why remove |
|---|---|
| `Server` | Fingerprint (CANNOT be removed in CloudFront — silently ignored) |
| `X-Powered-By` | Framework fingerprint (PHP, Express, etc.) |
| `X-AspNet-Version` | .NET framework fingerprint |
| `X-AspNetMvc-Version` | .NET MVC fingerprint |
| `Via` | Proxy fingerprint (CANNOT be removed in CloudFront) |

### Step 5: Managed policy selection

| Managed policy | When to use |
|---|---|
| `SecurityHeadersPolicy` (`0857826db9cffff310d5ad62955c9c26`) | Security headers only (HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy strict-origin-when-cross-origin) |
| `SimpleCORS` (`608323ce734e4449839d234493be9c7c`) | Simple CORS (no preflight); allows all origins |
| `CORS-with-preflight-and-SecurityHeadersPolicy` (`5cc3b908-e619-4b99-88e5-2ca770afe08f`) | Combined CORS + preflight + security headers |
| `CORSAndHTTPSecurityHeadersPolicy` (`e0bbb029-0798-45b7-9b86-9e6a1c2670e4`) | Combined CORS + security headers (no preflight) |

Always emit a custom policy if the operator's requirements differ from
any managed policy — managed policies cannot be modified.

### Step 6: Attach policy to distribution

The policy attaches to a cache behavior. Use
`get-distribution-config --id <id>` to retrieve the current config,
modify the target behavior's `ResponseHeadersPolicyId`, and call
`update-distribution` with the retrieved `ETag`.

```bash
ETAG=$(aws cloudfront get-distribution-config --id <id> \
  --query 'ETag' --output text)
aws cloudfront update-distribution --id <id> \
  --if-match "$ETAG" \
  --distribution-config file://updated-config.json
```

### Step 7: Emit template (READY_TO_DEPLOY) or gap (PREREQUISITES_MISSING)

If all pre-flight requirements pass, emit the complete response headers
policy template + the distribution update plan:
- `AWS::CloudFront::ResponseHeadersPolicy` (custom policy).
- OR the managed policy ID reference (for managed policy path).
- The `AWS::CloudFront::Distribution` update (set
  `ResponseHeadersPolicyId` on the target cache behavior).
- `AWS::CloudFront::CachePolicy` (if a new cache policy is also needed).

If any requirement is missing, emit `PREREQUISITES_MISSING` with the
specific gap and the exact CLI / IaC snippet to close it.

## Patterns — IaC templates

Full CloudFormation and Terraform templates for both custom and managed
policy paths live in `references/response-headers-policy-templates.md`.

The non-negotiable security headers config block (custom policy):

```text
SecurityHeadersConfig:
  ContentSecurityPolicy: { Content: "default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'", Override: true }
  StrictTransportSecurity: { AccessControlMaxAgeSec: 63072000, IncludeSubdomains: true, Preload: true, Override: true }
  XFrameOptions: { FrameOption: DENY, Override: true }
  XContentTypeOptions: { Override: true }
  ReferrerPolicy: { ReferrerPolicy: "strict-origin-when-cross-origin", Override: true }
  PermissionsPolicy: { Content: "camera=(), microphone=(), geolocation=(), payment=()", Override: true }
```

The non-negotiable CORS-with-credentials config block:

```text
CorsConfig:
  AccessControlAllowOrigins: { Items: ["https://app.example.com"], Quantity: 1 }
  AccessControlAllowMethods: { Items: ["GET", "POST", "OPTIONS"], Quantity: 3 }
  AccessControlAllowHeaders: { Items: ["Authorization", "Content-Type"], Quantity: 2 }
  AccessControlAllowCredentials: true   # REQUIRES specific origins, NOT "*"
  AccessControlExposeHeaders: { Items: ["X-Total-Count"], Quantity: 1 }
  AccessControlMaxAgeSec: 86400
  OriginOverride: true
```

## Diagnostic flows

### Headers not appearing in browser response

1. Verify the policy is attached to the correct cache behavior:
   `aws cloudfront get-distribution-config --id <id>` and check
   `ResponseHeadersPolicyId` on the target behavior.
2. Verify the distribution is in `Deployed` state (not `InProgress`).
3. Clear the browser cache and CloudFront edge cache
   (`aws cloudfront create-invalidation --distribution-id <id> --paths "/*"`).
4. Check that `Override: true` is set on each header — without it,
   origin-emitted headers win.

### CSP blocks legitimate site functionality

1. Open browser DevTools → Console. CSP violations are logged with
   the violating directive and resource.
2. Add the specific source to the CSP directive (e.g.,
   `script-src 'self' https://cdn.example.com`).
3. Avoid `'unsafe-inline'` and `'unsafe-eval'` unless absolutely
   necessary — they neuter CSP's XSS protection.

### CORS preflight failing

1. Verify `Access-Control-Allow-Methods` includes `OPTIONS`.
2. Verify the origin in the request matches
   `Access-Control-AllowOrigins` exactly (including scheme and port).
3. Check `Access-Control-Allow-Headers` includes every header the
   browser sends in the actual request (e.g., `Authorization`,
   `Content-Type`, `X-Requested-With`).

### HSTS breaking subdomains

1. If `IncludeSubDomains: true` was set and a subdomain is
   HTTP-only, browsers will refuse to load it.
2. Short-term fix: wait for the `max-age` to expire (or use a
   different browser).
3. Long-term fix: serve all subdomains over HTTPS, OR set
   `IncludeSubDomains: false`.

## Output format (per operation)

```text
OPERATION: <create | update | attach | audit>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <policy-name>
REQUIREMENTS:
  - [PASS] <requirement description>
  - [FAIL] <requirement description> — <gap>
IAC_TEMPLATE: <inline CloudFormation / Terraform template, or "(held in draft)">
MANUAL_GAPS:
  - GAP: <gap description>
    REMEDIATION: <exact CLI or IaC snippet to close the gap>
    REASON: <why this cannot be automated>
NOTES: <managed policy version, attach-vs-embed, distribution deploy state>
```

### Perfect example output — READY_TO_DEPLOY

```text
OPERATION: create
VERDICT: READY_TO_DEPLOY
TARGET: prod-security-headers-policy
REQUIREMENTS:
  - [PASS] Distribution E27TVSIEXAMPLE exists in Deployed state
  - [PASS] Target behavior DefaultCacheBehavior has no policy attached
  - [PASS] Origin app.example.com reachable on HTTPS
  - [PASS] CORS origin list consistent with cert SAN
  - [PASS] CSP compatible with site script inventory (no inline)
IAC_TEMPLATE:
  # CloudFormation AWS::CloudFront::ResponseHeadersPolicy (custom):
  #   SecurityHeadersConfig: CSP default-src 'self'; HSTS 2yr preload;
  #     X-Frame-Options DENY; X-Content-Type-Options nosniff;
  #     Referrer-Policy strict-origin-when-cross-origin;
  #     Permissions-Policy camera=(), microphone=(), geolocation=()
  #   CorsConfig: specific origins, GET/POST/OPTIONS, credentials true,
  #     max-age 86400
  # Plus AWS::CloudFront::Distribution update attaching policy ID.
  # Full template in references/response-headers-policy-templates.md.
MANUAL_GAPS: (none)
NOTES:
  - Distribution update requires ETag match (get-distribution-config first).
  - CloudFront invalidation recommended after attach (cache may serve old headers).
  - Test CSP in Report-Only mode first if site has unknown inline scripts.
```

### Perfect example output — PREREQUISITES_MISSING

```text
OPERATION: create
VERDICT: PREREQUISITES_MISSING
TARGET: prod-cors-policy
REQUIREMENTS:
  - [FAIL] CORS config uses Access-Control-Allow-Origin "*" with
    AllowCredentials: true. Browsers reject this combination.
  - [PASS] Distribution exists in Deployed state
IAC_TEMPLATE: (held in draft — apply after closing the gap below)
MANUAL_GAPS:
  - GAP: CORS policy combines wildcard origin with credentials.
    REMEDIATION:
      Change Access-ControlAllowOrigins from ["*"] to a specific origin list:
      aws cloudfront update-response-headers-policy --id <policy-id> \
        --response-headers-policy-config file://fixed-cors.json --if-match <etag>
    REASON: Browsers reject Access-Control-Allow-Origin: * with credentials.
      The CloudFront API does not validate this; the browser does.
NOTES:
  - Use specific origins for credentialed CORS, OR set AllowCredentials: false.
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
response headers policy that fails silently (no headers in browser,
CSP breaks site, CORS rejected) or a gap report that leaves the
operator stuck. Self-check EVERY emitted block against these rules.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT substitute markdown headings or camelCase variants.

```text
OPERATION: <create | update | attach | audit>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <policy-name>
REQUIREMENTS:
  - [PASS] <requirement description>
  - [FAIL] <requirement description> — <gap>
IAC_TEMPLATE: <inline CloudFormation / Terraform, or "(held in draft)">
MANUAL_GAPS:
  - GAP: <gap description>
    REMEDIATION: <exact CLI or IaC snippet to close the gap>
    REASON: <why this cannot be automated>
NOTES: <managed policy version, attach-vs-embed, distribution deploy state>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` when any requirement is
   `[FAIL]`.** A single `[FAIL]` MUST produce
   `VERDICT: PREREQUISITES_MISSING`.

2. **NEVER emit a `[FAIL]` requirement without a corresponding
   `MANUAL_GAPS` entry.** Every `[FAIL]` line MUST have a matching
   GAP/REMEDIATION/REASON block.

3. **NEVER emit a CORS config with `Access-Control-Allow-Origin: *`
   AND `Access-ControlAllowCredentials: true`.** Browsers reject this
   combination — CloudFront will serve it but the browser console
   shows a CORS error. Use specific origins or disable credentials.

4. **NEVER emit a response headers policy with `Override: false` on
   security headers.** Without `Override: true`, origin-emitted headers
   (often weak or absent) win over the policy values. Every security
   header MUST have `Override: true`.

5. **NEVER emit an HSTS config with `max-age=63072000` on a
   non-production distribution.** HSTS is irreversible for the
   `max-age` duration. Use `max-age=300` for testing; reserve the
   2-year duration for verified production sites.

6. **NEVER emit a `RemoveHeaders` list including `Server` or `Via`.**
   CloudFront injects these at the edge and silently ignores removal
   attempts. List only origin-emitted fingerprint headers.

7. **NEVER emit `IAC_TEMPLATE: (held in draft)` without listing which
   specific `[FAIL]` items blocked it.**

**Self-check before emit:**
- [ ] Any `[FAIL]` in REQUIREMENTS → VERDICT is PREREQUISITES_MISSING?
- [ ] Every `[FAIL]` has a matching GAP/REMEDIATION/REASON block?
- [ ] CORS: `*` origin NOT combined with credentials?
- [ ] Security headers all have `Override: true`?
- [ ] HSTS `max-age` appropriate for environment (300 test, 63072000 prod)?
- [ ] `RemoveHeaders` excludes `Server` and `Via`?

## Expert heuristic — top 5 non-obvious failure modes

The five failure modes below are the ones a naive header setup misses.
Each is silently wrong (no error in CloudFront, error only in browser
console).

1. **`Override: false` on security headers means origin values win.**
   If the origin emits no `Content-Security-Policy` and the policy
   sets one with `Override: false`, the browser sees no CSP. The fix
   is `Override: true` on every security header in the policy. The
   CloudFront API accepts `Override: false` silently — no warning.

2. **CSP `default-src 'self'` blocks inline event handlers.** Most
   legacy sites use `onclick="..."` attributes, which are inline
   scripts. CSP blocks them. The fix is CSP with `'unsafe-inline'`
   in `script-src` (weaker but functional) or refactoring to
   `addEventListener` (stronger but invasive).

3. **HSTS `includeSubDomains` breaks HTTP-only subdomains.** Once a
   browser sees HSTS with `includeSubDomains`, it refuses HTTP on ALL
   subdomains for the `max-age` duration. If `staging.example.com` is
   HTTP-only, it stops loading. The fix is to serve all subdomains
   over HTTPS, OR set `includeSubDomains: false`.

4. **CORS preflight (`OPTIONS`) requests hit the origin if not cached.**
   CloudFront forwards `OPTIONS` requests to the origin by default.
   If the origin does not handle `OPTIONS`, it returns 405 and the
   browser's actual request never fires. Set
   `AccessControl-MaxAgeSec: 86400` in the policy to cache preflight.

5. **Cached error responses do NOT get response headers policy
   applied.** If CloudFront serves a cached 403 or 404, the policy is
   not applied — only origin-sourced responses get the headers. To
   add security headers to error responses, configure custom error
   responses in the distribution with managed error pages.

## Anti-Patterns — NEVER do these things

- **NEVER emit a CORS policy with `Access-Control-Allow-Origin: *`
  AND `Access-Control-Allow-Credentials: true`.** Browsers reject this
  combination. Use specific origins or disable credentials.

- **NEVER emit security headers with `Override: false`.** Without
  override, origin values (often absent or weak) win over the policy.
  Every security header MUST have `Override: true`.

- **NEVER emit `X-Frame-Options: ALLOW-FROM`.** `ALLOW-FROM` is
  deprecated and ignored by modern browsers. Use `DENY` or
  `SAMEORIGIN`, and use CSP `frame-ancestors` for fine-grained control.

- **NEVER emit an HSTS `max-age=63072000` on a non-production site.**
  HSTS is irreversible for the duration. Use `max-age=300` for testing.

- **NEVER emit a `RemoveHeaders` list including `Server` or `Via`.**
   CloudFront injects these at the edge and silently ignores removal.

- **NEVER emit a CSP without testing in Report-Only mode first.** CSP
  `default-src 'none'` will block all resources on a site with inline
  scripts, external CDNs, or images from other domains. Test with
  `Content-Security-Policy-Report-Only` first.

- **NEVER emit a managed policy reference assuming it covers CORS
  preflight.** `SecurityHeadersPolicy` and `SimpleCORS` do NOT handle
  preflight. Use `CORS-with-preflight-and-SecurityHeadersPolicy` if
  preflight is needed.

- **NEVER auto-execute `update-distribution` without the ETag match.**
  `UpdateDistribution` requires the current ETag from
  `get-distribution-config`. Without it, the update fails with
  `PreconditionFailed`. Always snapshot via `get` first.

- **NEVER emit a response headers policy attached to a distribution in
  `InProgress` state.** The update fails with `InvalidIfMatchVersion`.
  Wait for `Deployed` state before attaching.

- **NEVER emit a custom header that overrides `Cache-Control` without
  verifying the cache policy.** If the cache policy honors
  `Cache-Control` from the origin, and the response headers policy
  overrides it, the cache behavior changes silently.

- **NEVER emit `Referrer-Policy: no-referrer` for a public marketing
  site.** `no-referrer` breaks analytics (Google Analytics uses the
  referrer for source attribution). Use `strict-origin-when-cross-origin`.

- **NEVER assume the response headers policy applies to cached errors.**
  Cached 4xx/5xx responses bypass the policy. Configure custom error
  responses for security headers on error pages.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-response-headers-policy`, `update-response-headers-policy`,
  `delete-response-headers-policy`, `update-distribution` to attach),
  emit: `CONFIRM: About to <operation> on policy <name> / distribution
  <id>. This affects <consequence>. Proceed? (yes/no)`.

- **Verify the distribution is in `Deployed` state.**
  `aws cloudfront get-distribution --id <id> --query 'Distribution.Status'`.

- **Snapshot the existing policy and distribution config.**
  `aws cloudfront get-response-headers-policy --id <id> --output json > /tmp/policy-backup.json`
  and `get-distribution-config --id <id> --output json > /tmp/dist-backup.json`.

- **Capture the ETag for `update-distribution`.** The
  `update-distribution` call requires `--if-match <etag>` from the
  latest `get-distribution-config`.

- **Before emitting CSP, verify the site's script inventory.** CSP
  blocks unknown inline scripts and external CDNs. A CSP audit
  (browser DevTools → Console with Report-Only mode) prevents
  breakage.

- **Before emitting HSTS with `includeSubDomains`, verify all
  subdomains serve HTTPS.** HTTP-only subdomains will break.

- Prefer additive changes (attach a policy to a new behavior) over
  destructive changes (remove a policy from an existing behavior).

## Recent AWS features (2024-2026)

- **Response headers policy managed updates (2024-2025):** AWS updated
  `SecurityHeadersPolicy` to add `Permissions-Policy` and tighten
  default CSP. Managed policies now auto-update on AWS schedule;
  custom policies are immutable once created.

- **CORS-with-preflight-and-SecurityHeadersPolicy managed policy
  (2024):** combines CORS with preflight handling and the security
  headers baseline in one managed policy. Reduces the need for custom
  policies when the operator needs both CORS + security.

- **CloudFront OAC + response headers integration (2024):** OAC-signed
  S3 origins now pass through the response headers policy unchanged.
  Previously, OAC could strip `Cache-Control` from S3 origins.

- **Permissions-Policy header support (2024):** the
  `PermissionsPolicyConfig` block in `SecurityHeadersConfig` is GA.
  Use to disable browser features (camera, microphone, geolocation).

- **Response headers policy CloudFormation support (2024):**
  `AWS::CloudFront::ResponseHeadersPolicy` is now fully supported in
  CloudFormation (previously required custom resources or CLI).

- **CloudFront KeyValueStore + response headers (2025):** for dynamic
  header values (e.g., per-user CSP nonces), use KeyValueStore +
  CloudFront Functions to read the nonce and inject it via the
  response headers policy override pattern.

## Domain

AWS CloudOps / CloudFront Networking — Response Headers Policy,
Security Headers, CORS Configuration, Managed Policy Selection,
Distribution Hardening.

## AWS documentation

- **CloudFront response headers policy** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/creating-response-headers-policies.html
- **Managed response headers policies** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/managed-response-headers-policies.html
- **Security headers reference** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-response-headers-policies.html#understanding-response-headers-policies-security
- **CORS reference** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/understanding-response-headers-policies.html#understanding-response-headers-policies-cors
- **Custom headers reference** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/using-managed-response-headers-policies.html
- **CloudFront response headers API** — https://docs.aws.amazon.com/cloudfront/latest/APIReference/API_ResponseHeadersPolicy.html
- **AWS CLI cloudfront response-headers-policy** — https://docs.aws.amazon.com/cli/latest/reference/cloudfront/create-response-headers-policy.html
- **OWASP Secure Headers Project** — https://owasp.org/www-project-secure-headers/
- **MDN Content-Security-Policy** — https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
