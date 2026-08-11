# Eval prompt: managed-securityheaders-policy-ready

Attach the managed SecurityHeadersPolicy to an existing distribution and
emit the standard VERDICT block.

Operation: attach
Policy: managed SecurityHeadersPolicy
  (ID: 0857826db9cffff310d5ad62955c9c26)
Distribution: E27TVSIEXAMPLE (Deployed)
Target behavior: DefaultCacheBehavior

```json
{
  "RequirementChecks": {
    "cloudfront.get-distribution.E27TVSIEXAMPLE": {
      "Status": "Deployed"
    },
    "cloudfront.get-distribution-config.E27TVSIEXAMPLE": {
      "DefaultCacheBehavior.ResponseHeadersPolicyId": ""
    },
    "cloudfront.get-response-headers-policy.0857826db9cffff310d5ad62955c9c26": {
      "ResponseHeadersPolicySummary.Type": "managed",
      "Name": "SecurityHeadersPolicy"
    }
  }
}
```
