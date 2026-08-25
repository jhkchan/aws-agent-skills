# Advanced patterns — CloudFront Response Headers Deployer

Expert knowledge, edge cases, and recent-feature notes moved out of SKILL.md
for progressive disclosure. Load on demand.

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

## Mindset — the three realities

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
