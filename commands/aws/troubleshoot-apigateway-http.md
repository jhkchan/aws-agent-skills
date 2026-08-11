---
description: Diagnoses Amazon API Gateway HTTP API failures through a ten-category diagnostic tree (routing, JWT authorizer, CORS, payload format version, Lambda proxy, timeout, throttling, VPC link, deployment, logging) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "API Gateway 4xx"
  - "API Gateway 5xx"
  - "API Gateway 502 Bad Gateway"
  - "API Gateway routing error"
  - "API Gateway $default route"
  - "API Gateway catch-all route"
  - "JWT authorizer denied API Gateway"
  - "API Gateway CORS error"
  - "Access-Control-Allow-Origin missing"
  - "payload format version mismatch"
  - "isBase64Encoded Lambda API Gateway"
  - "API Gateway Lambda proxy 502"
  - "API Gateway integration timeout"
  - "VPC link integration 502 API Gateway"
  - "API Gateway stage deployment"
  - "API Gateway auto-deploy"
  - "API Gateway throttling 429"
  - "API Gateway burst limit exceeded"
  - "access logging vs execution logging API Gateway"
  - "troubleshoot API Gateway HTTP API"
  - "diagnose API Gateway failure"
  - "HTTP API returns 403"
  - "HTTP API returns 502"
routes_to: apigateway-http-troubleshooter
---

# /aws:troubleshoot-apigateway-http

Activate the `apigateway-http-troubleshooter` skill and diagnose an
Amazon API Gateway HTTP API failure through the ten-category
diagnostic tree.

## What it does

Reads a symptom description (HTTP status code, error response body,
client context) plus the API configuration, then walks the
symptom-driven diagnostic tree to a root cause with positive evidence:

1. **Pre-flight** — API type (HTTP vs REST), stage auto-deploy status,
   route list, integration config, authorizer config. Short-circuits
   on wrong API type (HTTP vs REST) or undeployed stage.
2. **Symptom entry** — map the error to one of: JWT authorizer denial
   (403), route matching error (404), CORS preflight rejection, Lambda
   proxy 502 (payload format version or response shape), integration
   timeout (29s), throttling (429), stage deployment not live, VPC
   link connectivity, logging misconfig.
3. **Layer-specific probes** —
   - JWT: `get-authorizer`, identity source vs client header, issuer
     match, audience match against decoded token `aud` claim.
   - Routing: `get-routes`, route key exact match, `$default` catch-all,
     case sensitivity, trailing slash, method match.
   - CORS: `get-api` CorsConfiguration (HTTP API) or `get-method`
     OPTIONS (REST API); AllowOrigins, AllowMethods (OPTIONS),
     AllowHeaders, AllowCredentials.
   - Payload format version: `get-integration`
     PayloadFormatVersion (1.0 vs 2.0); `isBase64Encoded` in Lambda
     logs; handler body-parsing logic.
   - Lambda proxy 502: response shape (statusCode as integer, body as
     string, isBase64Encoded flag).
   - Integration timeout: 29s hard cap; backend duration vs cap.
   - Throttling: stage/route `RateLimit`, `BurstLimit`; WAF rate rules.
   - Stage deployment: `get-stage` AutoDeploy, LastDeploymentStatus;
     `create-deployment` history.
   - VPC link: `get-vpc-links`, `elbv2 describe-target-health`,
     NLB target group health, SG rules.
   - Logging: access log settings vs execution logging level.
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that matches
   the symptom) or INSUFFICIENT_DATA (critical config missing).

Emits a deterministic diagnostic block per target:

```text
TARGET: <api-id / stage / route-key>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <ROUTE_MATCHING | ROUTE_PRIORITY_CATCHALL | JWT_AUTHORIZER |
        CORS_MISCONFIG | PAYLOAD_FORMAT_VERSION |
        INTEGRATION_LAMBDA_PROXY | INTEGRATION_TIMEOUT |
        STAGE_DEPLOYMENT | THROTTLING_BURST | VPCLINK_CONNECTIVITY |
        LOGGING_MISCONFIG | PARAMETER_MAPPING | UNKNOWN>
EVIDENCE:
  - <observed symptom — HTTP status code and response body>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "API Gateway returns 502 on POST"
- "HTTP API returns 403 Forbidden"
- "Browser CORS error on API Gateway"
- "API Gateway Lambda proxy 502"
- "VPC link integration returns 502"
- "API Gateway throttling 429"
- "Route changes not live after update"
- "API Gateway returns 504 after 29 seconds"

A bare API ID + any error verb ("API failing", "502 from API Gateway")
also routes here via the orchestrator.

## Inputs

- Symptom description: HTTP status code, response body, client-side
  error, browser console error, intermittent vs persistent pattern.
- API configuration: ApiId, ProtocolType (HTTP vs REST), stage name,
  AutoDeploy flag, route keys, integration type and PayloadFormatVersion,
  authorizer type and config, CorsConfiguration.
- For live-account diagnosis: `get-api`, `get-routes`, `get-integration`,
  `get-stage`, `get-authorizer`, `get-vpc-links`, `filter-log-events`,
  `elbv2 describe-target-health`, `cloudwatch get-metric-statistics`.

## Outputs

- One diagnostic block per target API/route/stage.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: authorizer update, CORS config update, payload
  format version switch, handler fix, deployment creation, throttling
  adjustment, VPC link/NLB fix, or INSUFFICIENT_DATA with missing
  fields listed.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for API Gateway HTTP API
  failures).
- `/aws:troubleshoot-lambda-invocation` for deeper diagnosis when the
  Lambda handler behind the API Gateway integration is the root cause.
- `/aws:troubleshoot-vpc-connectivity` for deeper diagnosis when the
  VPC link / NLB connectivity is the root cause.
