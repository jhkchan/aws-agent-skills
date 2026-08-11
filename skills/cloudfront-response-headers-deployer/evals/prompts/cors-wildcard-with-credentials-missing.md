# Eval prompt: cors-wildcard-with-credentials-missing

Design a CORS response headers policy and emit the standard VERDICT block.

Operation: create
Policy name: prod-cors-policy
Distribution: E27TVSIEXAMPLE (Deployed)
CORS: origin "*", methods GET/POST/OPTIONS, credentials true

```json
{
  "RequirementChecks": {
    "cloudfront.get-distribution.E27TVSIEXAMPLE": {
      "Status": "Deployed"
    },
    "cors_config_review": {
      "AccessControlAllowOrigins": ["*"],
      "AccessControlAllowCredentials": true,
      "browser_rejected_combination": true
    }
  }
}
```
