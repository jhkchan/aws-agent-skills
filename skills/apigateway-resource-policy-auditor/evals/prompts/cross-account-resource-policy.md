# Eval prompt: cross-account-resource-policy

Audit the following API Gateway configuration for security exposure. Emit the
standard VERDICT block (API, VERDICT, REASON, FINDINGS, REMEDIATION).

API id: api-cross-account-resource-policy
Protocol type: REST
Endpoint type: REGIONAL
Resource policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "OpenInvoke",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:us-east-1:111111111111:api-cross-account-resource-policy/prod/*/users"
    }
  ]
}
```

Stage: prod (deployed)
Usage plans: plan-secure (throttle: rateLimit=100, burstLimit=200; quota: limit=10000, period=DAY) — associated with API key
WAF Web ACL: api-waf-acl (associated)

Methods:
  Resource: /users
    GET: authorizationType: AWS_IAM, apiKeyRequired: false
