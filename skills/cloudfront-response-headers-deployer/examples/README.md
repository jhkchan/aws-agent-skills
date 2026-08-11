# End-to-end usage scenario: cloudfront-response-headers-deployer

A walkthrough showing the skill designing a custom response headers
policy with security headers + CORS for a production CloudFront
distribution, then surfacing a PREREQUISITES_MISSING verdict when a CORS
config combines a wildcard origin with credentials. Each path includes
requirement checks, full template emission, and post-verification
guidance — contrasted with what a generic assistant misses.

## Input (user prompt)

> Create a response headers policy for prod-security-headers-policy on
> distribution E27TVSIEXAMPLE. Include CSP default-src 'self',
> HSTS 2yr preload, X-Frame-Options DENY, X-Content-Type-Options nosniff,
> Referrer-Policy strict-origin-when-cross-origin, Permissions-Policy
> disabling camera/microphone. CORS for https://app.example.com with
> credentials. Remove X-Powered-By.

```json
{
  "Operation": "create",
  "Policy name": "prod-security-headers-policy",
  "Distribution": "E27TVSIEXAMPLE",
  "RequirementChecks": {
    "cloudfront.get-distribution.E27TVSIEXAMPLE": {"Status": "Deployed"},
    "cloudfront.get-distribution-config.E27TVSIEXAMPLE": {
      "DefaultCacheBehavior.ResponseHeadersPolicyId": ""
    },
    "cloudfront.list-response-headers-policies": [],
    "curl.app.example.com": {"HTTPS": true},
    "site_script_audit": {"inline_scripts": false, "external_cdns": false},
    "subdomain_https_audit": {"all_subdomains_https": true}
  }
}
```

## Skill output — READY_TO_DEPLOY

```text
OPERATION: create
VERDICT: READY_TO_DEPLOY
TARGET: prod-security-headers-policy
REQUIREMENTS:
  - [PASS] Distribution E27TVSIEXAMPLE exists in Deployed state
  - [PASS] DefaultCacheBehavior has no existing ResponseHeadersPolicyId
  - [PASS] Origin app.example.com reachable on HTTPS
  - [PASS] CORS origin https://app.example.com matches cert SAN
  - [PASS] CSP compatible with site script audit (no inline, no external CDNs)
  - [PASS] All subdomains serve HTTPS (HSTS includeSubDomains safe)
  - [PASS] No existing policy named prod-security-headers-policy
IAC_TEMPLATE:
  Resources:
    ResponseHeadersPolicy:
      Type: AWS::CloudFront::ResponseHeadersPolicy
      Properties:
        ResponseHeadersPolicyConfig:
          Name: prod-security-headers-policy
          SecurityHeadersConfig:
            ContentSecurityPolicy:
              Content: "default-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
              Override: true
            StrictTransportSecurity:
              AccessControlMaxAgeSec: 63072000
              IncludeSubdomains: true
              Preload: true
              Override: true
            XFrameOptions:
              FrameOption: DENY
              Override: true
            XContentTypeOptions:
              Override: true
            ReferrerPolicy:
              ReferrerPolicy: strict-origin-when-cross-origin
              Override: true
            PermissionsPolicy:
              Content: "camera=(), microphone=(), geolocation=(), payment=()"
              Override: true
          CorsConfig:
            AccessControlAllowOrigins:
              Items: ["https://app.example.com"]
              Quantity: 1
            AccessControlAllowMethods:
              Items: ["GET", "POST", "OPTIONS"]
              Quantity: 3
            AccessControlAllowHeaders:
              Items: ["Authorization", "Content-Type"]
              Quantity: 2
            AccessControlAllowCredentials: true
            AccessControlMaxAgeSec: 86400
            OriginOverride: true
          RemoveHeadersConfig:
            Items:
              - Header: X-Powered-By
    # Plus: AWS::CloudFront::Distribution update setting
    # DefaultCacheBehavior.ResponseHeadersPolicyId to the policy ID.
MANUAL_GAPS: (none)
NOTES:
  - Distribution update requires ETag match (get-distribution-config first).
  - CloudFront invalidation recommended after attach (/* paths).
  - HSTS is irreversible for max-age duration; tested subdomain coverage.
  - CSP in Report-Only mode first if site evolves new inline scripts.
```

## Contrast — PREREQUISITES_MISSING (CORS wildcard + credentials)

```text
OPERATION: create
VERDICT: PREREQUISITES_MISSING
TARGET: prod-cors-policy
REQUIREMENTS:
  - [PASS] Distribution E27TVSIEXAMPLE exists in Deployed state
  - [FAIL] CORS config uses Access-Control-Allow-Origin "*" with
    AllowCredentials: true. Browsers reject this combination.
IAC_TEMPLATE: (held in draft — apply after closing the gap below)
MANUAL_GAPS:
  - GAP: CORS policy combines wildcard origin with credentials.
    REMEDIATION:
      Change AccessControlAllowOrigins from ["*"] to specific origins:
      aws cloudfront update-response-headers-policy --id <policy-id> \
        --response-headers-policy-config file://fixed-cors.json \
        --if-match <etag>
      Where fixed-cors.json has AccessControlAllowOrigins.Items set to
      ["https://app.example.com"] and AccessControlAllowCredentials: true.
    REASON: Browsers reject Access-Control-Allow-Origin: * with
      credentials. The CloudFront API does not validate this; the
      browser does at runtime.
NOTES:
  - Use specific origins for credentialed CORS, OR set
    AllowCredentials: false to keep the wildcard origin.
```

## What the skill caught that a generic assistant misses

1. **CORS `*` + credentials is browser-rejected.** A generic assistant
   emits the config as requested. The skill catches the combination
   before the operator ships a broken policy.

2. **`Override: true` is non-negotiable on security headers.** A
   generic assistant omits it. Without override, origin-emitted headers
   (often absent) win over the policy values.

3. **HSTS `includeSubDomains` requires subdomain HTTPS audit.** A
   generic assistant emits it blindly. The skill verifies all
   subdomains serve HTTPS before emitting `includeSubDomains: true`.

4. **Managed policy IDs are region/account-agnostic.** A generic
   assistant treats them as account-specific. The skill knows
   `SecurityHeadersPolicy` is always
   `0857826db9cffff310d5ad62955c9c26`.

5. **Managed `SecurityHeadersPolicy` does NOT include CSP.** A generic
   assistant claims it covers all security headers. The skill knows the
   managed policy omits CSP and Permissions-Policy.

6. **Distribution must be in `Deployed` state to attach.** A generic
   assistant attempts the update mid-deploy and fails. The skill checks
   the distribution state first.

7. **`Server` and `Via` cannot be removed.** A generic assistant lists
   them in `RemoveHeadersConfig`. The skill knows CloudFront injects
   these at the edge and silently ignores removal attempts.

8. **ETag is required for `update-distribution`.** A generic assistant
   omits `--if-match`. The skill always snapshots via
   `get-distribution-config` first.

9. **CONFIRM gate.** A generic assistant auto-executes
   `update-distribution`. The skill emits CONFIRM and waits.

10. **Cached error responses bypass the policy.** A generic assistant
    claims headers apply everywhere. The skill notes the limitation
    and recommends custom error responses.

## Slash-command invocation

```
/aws:deploy-cloudfront-response-headers
```

Or via the orchestrator:

```
/aws:pipeline
You: "add security headers to my CloudFront distribution E27TVSIEXAMPLE"
```

The orchestrator emits
`[Phase: Deploy | Skills routed: cloudfront-response-headers-deployer]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "add security headers to my CloudFront distribution"
# [Phase: Deploy | Skills routed: cloudfront-response-headers-deployer]
```

## Live-account follow-up (optional, requires AWS CLI)

After the policy is created and attached:

```bash
# Verify the policy exists
aws cloudfront get-response-headers-policy \
  --id <policy-id> \
  --profile default

# Verify the distribution is updated and Deployed
aws cloudfront get-distribution \
  --id E27TVSIEXAMPLE \
  --profile default \
  --query 'Distribution.Status'

# Create an invalidation to clear cached responses without headers
aws cloudfront create-invalidation \
  --distribution-id E27TVSIEXAMPLE \
  --paths "/*" \
  --profile default

# Smoke-test the headers in the browser response
curl -I https://app.example.com \
  -H "Origin: https://app.example.com" \
  | grep -iE "(content-security-policy|strict-transport|x-frame|x-content-type|referrer|permissions-policy|access-control)"
```
