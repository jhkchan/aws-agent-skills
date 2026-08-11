# Eval prompt: custom-security-headers-ready

Design a custom response headers policy and emit the standard VERDICT
block (OPERATION, VERDICT, TARGET, REQUIREMENTS, IAC_TEMPLATE,
MANUAL_GAPS, NOTES).

Operation: create
Policy name: prod-security-headers-policy
Distribution: E27TVSIEXAMPLE (Deployed)
Target behavior: DefaultCacheBehavior
Security headers: CSP `default-src 'self'; object-src 'none';
  frame-ancestors 'none'`; HSTS max-age=63072000 includeSubDomains
  preload; X-Frame-Options DENY; X-Content-Type-Options nosniff;
  Referrer-Policy strict-origin-when-cross-origin;
  Permissions-Policy camera=(), microphone=()
CORS: origin https://app.example.com, methods GET/POST/OPTIONS,
  headers Authorization/Content-Type, credentials true, max-age 86400
Custom headers: X-Content-Classification=Restricted
Removal headers: X-Powered-By

```json
{
  "RequirementChecks": {
    "cloudfront.get-distribution.E27TVSIEXAMPLE": {
      "Status": "Deployed"
    },
    "cloudfront.get-distribution-config.E27TVSIEXAMPLE": {
      "DefaultCacheBehavior.ResponseHeadersPolicyId": ""
    },
    "cloudfront.list-response-headers-policies": [],
    "curl.app.example.com": {
      "HTTPS": true
    },
    "cert.SAN": ["app.example.com"],
    "site_script_audit": {
      "inline_scripts": false,
      "external_cdns": false
    },
    "subdomain_https_audit": {
      "all_subdomains_https": true
    }
  }
}
```
