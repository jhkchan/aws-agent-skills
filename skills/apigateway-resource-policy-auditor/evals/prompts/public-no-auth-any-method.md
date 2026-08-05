# Eval prompt: public-no-auth-any-method

Audit the following API Gateway configuration for security exposure. Emit the
standard VERDICT block (API, VERDICT, REASON, FINDINGS, REMEDIATION).

API id: api-public-no-auth-any-method
Protocol type: REST
Endpoint type: EDGE
Resource policy: (none)
Stage: prod (deployed)
Usage plans: (none associated)
WAF Web ACL: (not associated)

Methods:
  Resource: /
    ANY: authorizationType: NONE, apiKeyRequired: false
