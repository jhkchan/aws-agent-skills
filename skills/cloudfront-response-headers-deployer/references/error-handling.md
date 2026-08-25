# Error handling — CloudFront Response Headers Deployer

Diagnostic flows for the failure modes a deployed policy hits at runtime.
Moved out of SKILL.md for progressive disclosure. Load on demand.

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
