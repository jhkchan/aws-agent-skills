# Baseline (no-skill) response: cross-account-resource-policy

This file captures what a generic assistant produces WITHOUT the
apigateway-resource-policy-auditor skill loaded.

---

This API has a resource policy that allows any principal to invoke it.
The policy grants execute-api:Invoke to Principal "*" on the /users
resource. The methods use AWS_IAM authentication, so callers still need
IAM permissions.

The API has a usage plan and WAF configured which is good. You should
consider tightening the resource policy to only allow specific accounts
instead of using a wildcard principal.
