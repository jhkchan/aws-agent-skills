---
description: Audit an API Gateway REST/HTTP API for public no-auth methods, API-key-as-auth misuse, cross-account resource policy, missing usage plans, and absent WAF Web ACL.
nl_triggers:
  - "audit this API Gateway"
  - "check API Gateway authorization"
  - "is my API publicly accessible"
  - "API Gateway no auth methods"
  - "authorizationType NONE"
  - "does my API have a usage plan"
  - "API Gateway rate limiting"
  - "does my API have WAF"
  - "cross-account API Gateway resource policy"
  - "API key required but no auth"
  - "execute-api:Invoke Principal star"
  - "API Gateway security audit"
  - "harden API Gateway"
  - "ANY method no auth"
  - "COGNITO_USER_POOLS check"
routes_to: apigateway-resource-policy-auditor
---

# /aws:audit-apigateway-resource-policy

Activate the `apigateway-resource-policy-auditor` skill and audit one or
more API Gateway REST/HTTP API configurations for security exposure.

## What it does

Reads API Gateway configuration (API metadata, methods, stage, resource
policy, usage plan, WAF status) and applies the ordered classification
logic:

1. Endpoint type gate — PRIVATE APIs skip the PUBLIC_NO_AUTH check.
2. Method authorization — ANY/NONE on EDGE/REGIONAL is PUBLIC_NO_AUTH;
   API key required is NOT authentication.
3. Usage plan / rate limiting — no plan = NO_RATE_LIMIT.
4. Resource policy cross-account — Principal "*" on execute-api:Invoke
   with no condition = CONFIG_GAP.
5. WAF Web ACL — not associated = CONFIG_GAP.
6. Aggregation — worst finding wins (PUBLIC_NO_AUTH > NO_RATE_LIMIT >
   CONFIG_GAP > OK).

Emits a deterministic VERDICT per API:

```text
API: <api-id>
VERDICT: PUBLIC_NO_AUTH | NO_RATE_LIMIT | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [PUBLIC_NO_AUTH] <finding description (Step Na)>
  - [CONFIG_GAP] <finding description (Step Nb)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste API Gateway configuration and ask any of:

- "audit this API Gateway"
- "is my API publicly accessible?"
- "check for methods with no auth"
- "does my API have a usage plan?"
- "is there a WAF on my API?"
- "is my resource policy too broad?"

A bare API id + any audit verb also routes here via the orchestrator.

## Inputs

- API metadata: protocolType (REST/HTTP), endpointType (EDGE/REGIONAL/PRIVATE).
- Methods: per resource/method, the authorizationType, apiKeyRequired,
  and authorizerId.
- Resource policy JSON (REST APIs only).
- Stage deployment status.
- Usage plan: name, throttle, quota, and associated API keys.
- WAF Web ACL: name and association status.

## Outputs

- One VERDICT block per API (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: set authorizationType, create usage plan,
  associate WAF, scope resource policy.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for API Gateway security).
- `/aws:audit-wafv2-web-acl` for deep WAF Web ACL rule analysis.
- `/aws:audit-iam-least-privilege` for IAM policy analysis of roles that
  may have execute-api:Invoke permissions.
