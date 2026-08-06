# Eval prompt: api-key-not-auth

Audit the following API Gateway configuration for security exposure. Emit the
standard VERDICT block (API, VERDICT, REASON, FINDINGS, REMEDIATION).

API id: api-api-key-not-auth
Protocol type: REST
Endpoint type: REGIONAL
Resource policy: (none)
Stage: prod (deployed)
Usage plans: (none associated)
WAF Web ACL: (not associated)

Methods:
  Resource: /orders
    GET: authorizationType: NONE, apiKeyRequired: true
