# Baseline (no-skill) response: api-key-not-auth

This file captures what a generic assistant produces WITHOUT the
apigateway-resource-policy-auditor skill loaded.

---

This API has a GET method on /orders that requires an API key but does
not have an authorization type set. The API key provides some protection
since callers need to know the key to access the endpoint.

There is no usage plan or WAF configured. You might want to add IAM or
Cognito authentication for stronger security, but the API key does
provide a basic level of access control.
