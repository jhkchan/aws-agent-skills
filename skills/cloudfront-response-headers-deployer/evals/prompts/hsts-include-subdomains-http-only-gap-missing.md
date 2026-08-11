# Eval prompt: hsts-include-subdomains-http-only-gap-missing

Design an HSTS response headers policy and emit the standard VERDICT
block.

Operation: create
Policy name: prod-hsts-policy
Distribution: E27TVSIEXAMPLE (Deployed)
HSTS: max-age=63072000, includeSubDomains=true, preload=true
Domain: example.com
Subdomains: app.example.com (HTTPS), staging.example.com (HTTP-only)

```json
{
  "RequirementChecks": {
    "cloudfront.get-distribution.E27TVSIEXAMPLE": {
      "Status": "Deployed"
    },
    "subdomain_https_audit": {
      "app.example.com": {"HTTPS": true},
      "staging.example.com": {"HTTPS": false, "HTTP_only": true}
    }
  }
}
```
