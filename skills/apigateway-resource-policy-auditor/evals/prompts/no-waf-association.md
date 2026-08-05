# Eval prompt: no-waf-association

Audit the following API Gateway configuration for security exposure. Emit the
standard VERDICT block (API, VERDICT, REASON, FINDINGS, REMEDIATION).

API id: api-no-waf-association
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
      "Resource": "arn:aws:execute-api:us-east-1:111111111111:api-no-waf-association/*",
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
Usage plans: plan-secure (throttle: rateLimit=50, burstLimit=100; quota: limit=5000, period=DAY) — associated with API key
WAF Web ACL: (not associated)

Methods:
  Resource: /profile
    GET: authorizationType: COGNITO_USER_POOLS, authorizerId: abc123, apiKeyRequired: false
