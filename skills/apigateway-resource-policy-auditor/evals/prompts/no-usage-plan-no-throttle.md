# Eval prompt: no-usage-plan-no-throttle

Audit the following API Gateway configuration for security exposure. Emit the
standard VERDICT block (API, VERDICT, REASON, FINDINGS, REMEDIATION).

API id: api-no-usage-plan-no-throttle
Protocol type: REST
Endpoint type: REGIONAL
Resource policy: (none — same-account default access)
Stage: prod (deployed)
Usage plans: (none associated)
WAF Web ACL: (not associated)

Methods:
  Resource: /data
    GET: authorizationType: AWS_IAM, apiKeyRequired: false
    POST: authorizationType: AWS_IAM, apiKeyRequired: false
