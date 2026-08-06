# Eval prompt: all-controls-ok

Audit the following API Gateway configuration for security exposure. Emit the
standard VERDICT block (API, VERDICT, REASON, FINDINGS, REMEDIATION).

API id: api-all-controls-ok
Protocol type: REST
Endpoint type: REGIONAL
Resource policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SameAccountOnly",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:us-east-1:111111111111:api-all-controls-ok/*",
      "Condition": {
        "StringNotEquals": {
          "aws:SourceAccount": "111111111111"
        }
      }
    }
  ]
}
```

Stage: prod (deployed)
Usage plans: plan-prod (throttle: rateLimit=50, burstLimit=100; quota: limit=5000, period=DAY) — associated with API key
WAF Web ACL: prod-waf-acl (associated, includes AWSManagedRulesCommonRuleSet and a rate-based rule)

Methods:
  Resource: /items
    GET: authorizationType: COGNITO_USER_POOLS, authorizerId: usrpool-auth, apiKeyRequired: false
    POST: authorizationType: COGNITO_USER_POOLS, authorizerId: usrpool-auth, apiKeyRequired: false
