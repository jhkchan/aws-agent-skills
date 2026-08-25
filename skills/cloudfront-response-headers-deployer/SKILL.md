---
name: cloudfront-response-headers-deployer
description: 'Provisions CloudFront response headers policies with secure defaults: security headers (Content-Security-Policy, Strict-Transport-Security, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy), CORS configuration (access-control-allow-origin, methods, headers, credentials, expose-headers, max-age, preflight), custom headers (Cache-Control, X-Custom), removal headers (Server, X-Powered-By), managed policies (CORS-with-preflight-and-SecurityHeadersPolicy, SimpleCORS, CORSAndHTTPSecurityHeadersPolicy, SecurityHeadersPolicy), and the latest CloudFront response headers policy managed updates. Emits a deployment plan with a verdict (READY_TO_DEPLOY with full CloudFormation / Terraform template | PREREQUISITES_MISSING with specific gap and remediation). Use when provisioning security headers on a CloudFront distribution, configuring CORS for cross-origin access, attaching managed SecurityHeadersPolicy, removing server fingerprint headers, or hardening a CDN''s HTTP response posture.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws cloudfront create-response-headers-policy, get-response-headers-policy, update-response-headers-policy, delete-response-headers-policy, list-response-headers-policies, create-response-headers-policy-config, get-distribution-config, update-distribution, create-distribution, list-conflicting-aliases, and aws cloudfront...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning a CloudFront response headers policy for security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy); configuring CORS for cross-origin access (simple CORS, preflight, credentials); attaching a managed policy (SecurityHeadersPolicy, CORSAndHTTPSecurityHeadersPolicy, SimpleCORS, CORS-with-preflight-and-SecurityHeadersPolicy); removing server fingerprint headers (Server, X-Powered-By); setting custom headers (Cache-Control, X-Custom); or hardening a distribution's HTTP response posture before production.
  activation_triggers: create CloudFront response headers policy, CloudFront security headers, CloudFront CSP, CloudFront HSTS, CloudFront X-Frame-Options, CloudFront CORS, CloudFront access-control-allow-origin, CloudFront preflight, CloudFront managed SecurityHeadersPolicy, CloudFront SimpleCORS, CloudFront remove Server header, CloudFront remove X-Powered-By, CloudFront Cache-Control header, CloudFront Permissions-Policy, CloudFront Referrer-Policy, attach response headers policy to distribution
  invocation_schema: 'Input shape (one of): (a) a deployment spec describing header requirements (security headers + values, CORS origin/methods/headers, custom headers, removal headers, managed vs custom policy); (b) a partial spec for interactive refinement ("security headers on my distribution"); (c) an existing distribution ID for policy review against the secure-defaults checklist. Output shape: { POLICY_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudFront, response headers policy, security headers, Content-Security-Policy, CSP, Strict-Transport-Security, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, CORS, access-control-allow-origin, preflight, managed policy, SecurityHeadersPolicy, SimpleCORS, Cache-Control, custom headers, removal headers, Server header, X-Powered-By
  tags: cloudfront, networking, deploy, security-headers, cors, response-headers-policy, cdn, hardening
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

→ The three realities (Lambda@Edge replacement, wildcard+credentials silent rejection, fixed managed IDs) — `references/advanced-patterns.md`.

## Pre-flight: requirement gate

Run before emitting any template. Missing requirements produce
PREREQUISITES_MISSING with the exact gap.

**Live-account pre-flight (skip if offline plan audit):**
→ Full 6-check CLI listing (distribution Deployed state, policy inventory + snapshot, origin HTTPS, cache-policy conflict, managed ID) — `references/diagnostic-commands.md`.

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
→ All 12 non-obvious behaviors (immutable+ETag, Server/Via, CSP baseline, XFO redundancy, HSTS preload, preflight cache, credentials, override, managed auto-update, cached errors, behavior attach, Permissions-Policy) — `references/advanced-patterns.md`.

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

→ The two non-negotiable config blocks (SecurityHeadersConfig + credentialed CorsConfig) — `references/response-headers-policy-templates.md`.

## Diagnostic flows

→ All four flows (headers not appearing, CSP breakage, CORS preflight failure, HSTS breaking subdomains) — `references/error-handling.md`.

## Output format (per operation)

→ Full per-operation label contract — `references/worked-examples.md` (the STRICT output contract below remains authoritative).

### FORBIDDEN output patterns — NEVER

1. NEVER emit `VERDICT: READY_TO_DEPLOY` while any CHECKLIST item is
   `[ ]` (unchecked). A single unchecked item forces
   `PREREQUISITES_MISSING`.

2. NEVER emit a CORS config with `Access-Control-Allow-Origin: *`
   combined with `AllowCredentials: true`. Browsers reject this
   combination silently — CloudFront serves the headers, the browser
   console shows the CORS error, and no CloudFront metric fires.

3. NEVER emit security headers with `Override: false`. Without
   `Override: true`, origin-emitted headers (often absent or weak) win
   over the policy. The CloudFront API accepts `Override: false`
   silently. Every security header in the policy MUST be `Override: true`.

4. NEVER emit `HSTS: max-age=63072000; includeSubDomains; preload` on a
   non-production distribution. HSTS is irreversible for the `max-age`
   duration — once a browser sees it, all subdomains are HTTPS-only for
   2 years. Use `max-age=300` for testing; reserve the 2-year duration
   for verified production sites.

5. NEVER emit a `RemoveHeaders` list that includes `Server` or `Via`.
   CloudFront injects these at the edge and silently ignores removal
   attempts. List only origin-emitted fingerprint headers
   (`X-Powered-By`, `X-AspNet-Version`).

6. NEVER emit `X-Frame-Options: ALLOW-FROM`. `ALLOW-FROM` is deprecated
   and ignored by modern browsers. Use `DENY` or `SAMEORIGIN`, and use
   CSP `frame-ancestors` for fine-grained control.

7. NEVER auto-execute `update-distribution` without the current ETag
   from `get-distribution-config`. Without `--if-match <etag>`, the
   update fails with `PreconditionFailed` and provides no warning
   during planning.

### Worked example — READY_TO_DEPLOY (distribution with HSTS + X-Frame-Options + CSP)

```text
DISTRIBUTION_ID: E27TVSIEXAMPLE1A
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [x] Target distribution: E27TVSIEXAMPLE1A exists in Deployed state (verified via get-distribution-config)
  [x] Target behavior: DefaultCacheBehavior (PathPattern: * — catch-all)
  [x] Response headers policy:
        - Security headers:
            Content-Security-Policy: "default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
            Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
            X-Frame-Options: DENY
            X-Content-Type-Options: nosniff
            Referrer-Policy: strict-origin-when-cross-origin
            Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
        - CORS: not configured (same-origin app — no cross-origin requirements)
        - Custom headers: X-Content-Classification=Restricted, X-Service-Version=1.2.3
        - Removal headers: X-Powered-By, X-AspNet-Version (CloudFront Server/Via intentionally not listed — cannot be removed)
  [x] Policy origin: custom (managed SecurityHeadersPolicy does not include CSP frame-ancestors 'none' + Permissions-Policy simultaneously)
  [x] Override: true on every security header (CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
  [x] Attach plan: get-distribution-config E27TVSIEXAMPLE1A → capture ETag → update-distribution with --if-match
GAP: None
IAC_TEMPLATE:
  # CloudFormation — AWS::CloudFront::ResponseHeadersPolicy (custom) +
  # AWS::CloudFront::Distribution update attaching policy ID to DefaultCacheBehavior
  SecurityHeadersConfig:
    ContentSecurityPolicy: { Content: "default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'", Override: true }
    StrictTransportSecurity: { AccessControlMaxAgeSec: 63072000, IncludeSubdomains: true, Preload: true, Override: true }
    FrameOptions: { FrameOption: DENY, Override: true }
    ContentTypeOptions: { Override: true }
    ReferrerPolicy: { ReferrerPolicy: "strict-origin-when-cross-origin", Override: true }
    PermissionsPolicy: { Content: "camera=(), microphone=(), geolocation=(), payment=()", Override: true }
  CustomHeadersConfig:
    Items:
      - { Header: { Value: Restricted }, Name: X-Content-Classification, Override: true }
      - { Header: { Value: 1.2.3 }, Name: X-Service-Version, Override: true }
  RemoveHeadersConfig:
    Items: [X-Powered-By, X-AspNet-Version]
  # Full CloudFormation / Terraform template in references/response-headers-policy-templates.md
MANUAL_GAPS: (none)
NOTES:
  - Distribution update requires ETag match — call get-distribution-config E27TVSIEXAMPLE1A first.
  - CloudFront invalidation recommended after attach: aws cloudfront create-invalidation --distribution-id E27TVSIEXAMPLE1A --paths "/*"
  - Test CSP in Report-Only mode first if site has unknown inline scripts.
  - HSTS max-age=63072000 with includeSubDomains is irreversible for 2 years — confirm all subdomains serve HTTPS before deploy.
```

### Worked example — PREREQUISITES_MISSING (wildcard CORS + credentials)
→ Full example block — `references/worked-examples.md`.

### Decision tree — managed policy vs custom policy

```
Start: response headers requirement
├─ CORS required?
│   ├─ Yes → Preflight (OPTIONS) needed?
│   │   ├─ Yes → CORS-with-preflight-and-SecurityHeadersPolicy (managed ID 5cc3b908-e619-4b99-88e5-2ca770afe08f)
│   │   │         if security headers also needed; else custom (no managed
│   │   │         preflight-only policy)
│   │   └─ No  → CORSAndHTTPSecurityHeadersPolicy (managed ID e0bbb029-0798-45b7-9b86-9e6a1c2670e4)
│   │            OR SimpleCORS (managed ID 608323ce734e4449839d234493be9c7c) if no security headers
│   └─ No  → Security headers only?
│            ├─ Default OWASP baseline sufficient?
│            │   ├─ Yes → SecurityHeadersPolicy (managed ID 0857826db9cffff310d5ad62955c9c26)
│            │   └─ No  → Custom (CSP / Permissions-Policy / HSTS tweak required)
│            └─ Custom or removal headers needed?
│                └─ Yes → Custom policy (managed policies cannot be modified)
└─ Wildcard origin "*" with credentials true? → ALWAYS PREREQUISITES_MISSING
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
→ All five failure modes (Override:false, CSP vs inline handlers, HSTS includeSubDomains, uncached preflight, cached-error bypass) — `references/advanced-patterns.md`.

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

→ Full checklist (confirmation gate, Deployed-state verify, snapshots, ETag capture, CSP inventory, HSTS subdomain check) — `references/diagnostic-commands.md`.

## Recent AWS features (2024-2026)

→ All six updates (managed policy updates, CORS-with-preflight, OAC, Permissions-Policy GA, CloudFormation, KeyValueStore) — `references/advanced-patterns.md`.

## References (load on demand)

- [`references/worked-examples.md`](references/worked-examples.md) — secondary worked example (PREREQUISITES_MISSING wildcard CORS) + per-operation output format spec
- [`references/error-handling.md`](references/error-handling.md) — diagnostic flows: headers not appearing, CSP breakage, CORS preflight failure, HSTS breaking subdomains
- [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — live-account pre-flight commands; pre-remediation safety checks
- [`references/advanced-patterns.md`](references/advanced-patterns.md) — Step 0 non-obvious behaviors, expert-heuristic failure modes, mindset realities, recent AWS features (2024-2026)
- [`references/response-headers-policy-templates.md`](references/response-headers-policy-templates.md) — full IaC templates (pre-existing) + non-negotiable config blocks
- [`references/security-headers-and-managed-policies.md`](references/security-headers-and-managed-policies.md) — header semantics + managed policy matrix (pre-existing)

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
