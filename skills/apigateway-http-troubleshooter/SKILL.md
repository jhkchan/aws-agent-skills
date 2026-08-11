---
name: apigateway-http-troubleshooter
description: >-
  Diagnoses Amazon API Gateway HTTP API failures through a ten-category
  diagnostic tree: 4xx routing errors ($default route, catch-all route
  priority, ANY vs explicit method), 5xx integration failures (Lambda
  proxy 502, private integration 502, timeout at 29s hard cap), JWT
  authorizer failures (issuer, audience, claim mapping, scope), CORS
  preflight errors (Access-Control-Allow-Origin, OPTIONS method,
  AllowHeaders), payload format version mismatches (1.0 vs 2.0 event
  body base64 decode, isBase64Encoded, requestContext shape), stage
  deployment issues (changes not live without deployment, auto-deploy
  vs manual), throttling and burst limits (rate, burst, per-route),
  access logging vs execution logging confusion, VPC link integration
  problems (NLB target health, private integration connectivity), and
  integration parameter mapping errors. Walks symptoms to a verified
  root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED
  or INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error responses and API configuration. Live-account
  diagnosis uses aws apigatewayv2 get-api, get-route, get-integration, get-stage, get-authorizer, export-api, aws apigateway get-rest-api / get-resources / get-stage / get-method (for REST APIs), aws logs
  filter-log-events, aws elbv2 describe-target-health, and aws cloudwatch get-metric-statistics (AWS CLI v2, SSO or key-based credentials).
keywords:
- API Gateway
- HTTP API
- REST API
- 4xx
- 5xx
- routing
- $default route
- catch-all
- JWT authorizer
- CORS
- preflight
- payload format version
- isBase64Encoded
- Lambda proxy
- 502 Bad Gateway
- integration timeout
- VPC link
- NLB
- private integration
- stage deployment
- auto-deploy
- throttling
- burst limit
- access logging
- execution logging
tags:
- apigateway
- networking
- app-integration
- troubleshooting
- http-api
- jwt
- cors
- vpclink
- throttling
- routing
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an API Gateway HTTP API failure (4xx routing error, 5xx integration failure, JWT authorizer denial, CORS preflight rejection, payload format version mismatch, Lambda proxy 502,
    integration timeout, VPC link connectivity, stage deployment not live, throttling), walking a symptom to the failed layer with verify and fix commands, validating why a client request returns an error,
    or triaging a "the API is broken" page where the root cause may be route config, authorizer, CORS, integration mapping, stage, or network.
  when_not_to_use: Application-level debugging of the Lambda handler (use lambda-invocation-troubleshooter), CloudFront distribution or edge issues (use CloudFront logs), AppSync GraphQL resolver debugging
    (use AppSync resolver logs), or WAF rule tuning (use waf-rule-auditor). This skill diagnoses API-Gateway-layer failures; it does not debug the backend handler code or audit IAM posture of API callers.
  activation_triggers:
  - API Gateway 4xx
  - API Gateway 5xx
  - API Gateway 502 Bad Gateway
  - API Gateway routing error
  - $default route
  - API Gateway catch-all route
  - JWT authorizer denied
  - API Gateway CORS error
  - Access-Control-Allow-Origin missing
  - payload format version mismatch
  - isBase64Encoded Lambda
  - API Gateway Lambda proxy 502
  - API Gateway integration timeout
  - VPC link integration 502
  - API Gateway stage deployment
  - API Gateway auto-deploy
  - API Gateway throttling 429
  - API Gateway burst limit exceeded
  - access logging vs execution logging
  - troubleshoot API Gateway HTTP API
  invocation_schema: 'Input: either (a) a symptom description (HTTP status code, error response body, client-side error, "API returns 403", "POST returns 502") optionally paired with the API configuration
    (get-api/get-rest-api output, route list, integration config, stage config, authorizer config), OR (b) an API identifier (api-id) plus request context (method, path, headers, caller identity) for live-account
    diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {ROUTE_MATCHING, ROUTE_PRIORITY_CATCHALL,
    JWT_AUTHORIZER, CORS_MISCONFIG, PAYLOAD_FORMAT_VERSION, INTEGRATION_LAMBDA_PROXY, INTEGRATION_TIMEOUT, STAGE_DEPLOYMENT, THROTTLING_BURST, VPCLINK_CONNECTIVITY, LOGGING_MISCONFIG, PARAMETER_MAPPING,
    UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"HTTP API abc1234 returns 502 Bad Gateway on POST /orders\nonly when the request body exceeds 1 KB; GET requests
    to the\nsame route succeed.\"\nApiId: abc1234\nProtocolType: HTTP\nIntegrationType: AWS_PROXY\nIntegrationSubtype: Lambda\nPayloadFormatVersion: \"2.0\"\nRouteKey: POST /orders\nStage: $default\nAutoDeploy:
    true\nLastError: \"Internal Server Error\""
---

# API Gateway HTTP API Troubleshooter

## Quick Navigation

| Section | Purpose |
|---|---|
| Quick start | Symptom → layer map, core rules |
| Diagnostic decision tree | Step-by-step probes per layer |
| Output format | Strict contract + worked examples |
| Anti-Patterns (NEVER) | Top mistakes to avoid |
| Expert heuristic | Payload version + JWT + route priority |
| Configuration dependency graph | Visual troubleshooting flow |

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  403 Forbidden → JWT_AUTHORIZER; 404 on a known route →
  ROUTE_MATCHING / ROUTE_PRIORITY_CATCHALL; CORS error in browser →
  CORS_MISCONFIG; 502 from Lambda → INTEGRATION_LAMBDA_PROXY /
  PAYLOAD_FORMAT_VERSION; 502/504 after ~29s → INTEGRATION_TIMEOUT;
  429 → THROTTLING_BURST; changes "not live" after update →
  STAGE_DEPLOYMENT; 502 from VPC link → VPCLINK_CONNECTIVITY;
  no logs → LOGGING_MISCONFIG.

- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_IDENTIFIED verdict
  requires positive evidence — a failing probe matching the symptom.

- **HTTP API (apigatewayv2) and REST API (apigateway) are different
  services.** HTTP APIs use `aws apigatewayv2`; REST APIs use
  `aws apigateway`. Payload format versions, authorizer models, route
  keys, and stage semantics all differ. Always identify the API type
  first via `get-api` vs `get-rest-api`.

- **Payload format version 2.0 may base64-encode the body.** Lambda
  integrations on HTTP APIs default to `PayloadFormatVersion: 2.0`.
  Handlers written for v1.0 that read `event.body` as raw JSON
  silently break when v2.0 delivers a base64-encoded body with
  `isBase64Encoded: true`.

- **Route priority is exact-match-first, then variable, then
  `$default`.** `GET /orders` matches before `GET /orders/{id}`;
  both match before `$default`. Operators who add a route but forget
  to deploy see `$default` swallow the traffic.

- **INSUFFICIENT_DATA for missing context.** If the symptom cannot be
  routed to a failing probe because critical config (integration URI,
  authorizer ID, stage auto-deploy flag, VPC link ID) is absent, emit
  INSUFFICIENT_DATA and list exactly what is missing.

## Mindset

A failing API Gateway HTTP API is usually a configuration, mapping, or
deployment issue wearing a backend-code costume. The integration is
fine in the majority of cases; the broken thing is route priority, JWT
claim mapping, CORS headers, payload format version, stage deployment,
throttling, or VPC link connectivity. Treat the backend handler as
innocent until the route, authorizer, integration, and stage layers
are proven clean.

## Philosophy

- **The HTTP status code drives the diagnostic order.** A `403` with a
  JWT authorizer means the authorizer denied the request. A `502` with
  a Lambda integration means API Gateway could not parse the response.
  A `504` or `502` after exactly 29 seconds means the integration
  timed out. Routing the symptom to the wrong layer is the #1 source
  of wasted cycles.

- **Payload format version 2.0 is the single most common silent-break
  for Lambda integrations on HTTP APIs.** The v2.0 event wraps the body
  differently, flattens headers, and base64-encodes binary content. A
  handler that worked on a REST API (v1.0) silently breaks on POST
  bodies after migration to HTTP API (v2.0).

- **Route priority evaluation is deterministic but non-obvious.**
  Exact match → greedy (variable) match → `$default`. If `$default` is
  configured, any request not matching an explicit route falls through
  to it, masking undeployed or mis-keyed routes.

- **Stage deployment is mandatory for REST APIs and optional
  (auto-deploy) for HTTP APIs — but auto-deploy can be disabled.** An
  HTTP API stage with `AutoDeploy: false` requires manual
  `create-deployment`.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `403 Forbidden`, `{"message":"User is not authorized"}}` | JWT_AUTHORIZER | `get-authorizer`, JWT issuer/audience/identity source |
| `404 Not Found` on a known route | ROUTE_MATCHING / ROUTE_PRIORITY_CATCHALL | `get-routes`, route key match, `$default` catch-all |
| Browser CORS: `Access-Control-Allow-Origin` missing | CORS_MISCONFIG | `get-api` CorsConfiguration (HTTP) or get-method OPTIONS (REST) |
| `502 Bad Gateway` from Lambda proxy | INTEGRATION_LAMBDA_PROXY / PAYLOAD_FORMAT_VERSION | `get-integration` PayloadFormatVersion, Lambda response shape |
| `502` / `504` after ~29 seconds | INTEGRATION_TIMEOUT | Integration timeout setting, backend duration |
| `429 Too Many Requests` | THROTTLING_BURST | Stage/route throttling config |
| Config changed but "not live" | STAGE_DEPLOYMENT | `get-stage` AutoDeploy, deployment history |
| `502` from private integration / VPC link | VPCLINK_CONNECTIVITY | `get-vpc-links`, `elbv2 describe-target-health` |
| Traffic flows but no logs | LOGGING_MISCONFIG | Stage access log settings, execution logging level |
| Lambda receives garbled / base64 body | PAYLOAD_FORMAT_VERSION | Integration PayloadFormatVersion 1.0 vs 2.0 |
| None of the above | UNKNOWN / INSUFFICIENT_DATA | Gather API type, full request/response, integration config |

## Pre-flight: API state and gather-info gate

```bash
# 1. API metadata (type, protocol, endpoint)
aws apigatewayv2 get-api --api-id <api-id> --output json

# 2. All routes (route key, target, authorizer)
aws apigatewayv2 get-routes --api-id <api-id> --output json

# 3. Integration details (type, connection, payload format version)
aws apigatewayv2 get-integration --api-id <api-id> \
  --integration-id <id> --output json

# 4. Stage configuration (auto-deploy, throttling, access logs)
aws apigatewayv2 get-stage --api-id <api-id> --stage-name <stage> --output json

# 5. Authorizer configuration (type, issuer, audience, identity source)
aws apigatewayv2 get-authorizer --api-id <api-id> \
  --authorizer-id <id> --output json

# 6. Recent execution logs (if execution logging enabled)
aws logs filter-log-events \
  --log-group-name /aws/apigateway/<api-id>/<stage> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"403" OR "502" OR "504" OR "429" OR "ERROR"' \
  --output json

# 7. VPC links (for private integrations)
aws apigatewayv2 get-vpc-links --output json

# 8. CloudWatch 5XX metrics
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiId,Value=<api-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

### API-type identification short-circuit

| Field | Effect |
|---|---|
| `ProtocolType: HTTP` | HTTP API (apigatewayv2). Use apigatewayv2 CLI. |
| `ProtocolType: WEBSOCKET` | WebSocket API. Different routing model. Not covered. |
| REST API (`get-rest-api`) | REST API (apigateway). Use apigateway CLI. |

If input is malformed (missing ApiId, absent symptom description), emit:

```text
TARGET: <api-id or unknown>
VERDICT: INSUFFICIENT_DATA
REASON: Input is missing required context — at minimum a symptom
  description (HTTP status code, error body) and the ApiId.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact HTTP status code
  and response body, (2) the ApiId and API type (HTTP vs REST), and
  (3) the request context (method, path, headers, authorizer).
```

## Diagnostic decision tree

### Step 0: Non-obvious behaviours that change diagnosis

- **Payload format version 2.0 base64-encodes binary and non-JSON
  bodies.** A handler that does `JSON.parse(event.body)` on a base64
  string throws. Check `event.isBase64Encoded` and decode first, or
  switch to `PayloadFormatVersion: 1.0`.

- **JWT authorizer identity source controls which claim is evaluated.**
  If the client sends the token in a different header than
  `IdentitySource` specifies, the authorizer sees an empty string and
  denies with 403.

- **JWT audience must match the `aud` claim exactly.** Case-sensitive.
  Authorizer `Audience: ["client-1"]` denies a token with
  `aud: ["client-2"]`.

- **Route priority: exact → greedy → `$default`.** `$default` is
  intentional but masks undeployed or mis-keyed routes.

- **The 29-second integration timeout is NOT tunable.** If the backend
  takes longer, API Gateway returns 504 (REST) or 502 (HTTP). Move
  long-running work to async.

- **`AutoDeploy: true` may not pick up authorizer or access-log
  changes.** When in doubt, run `create-deployment` explicitly.

- **CORS on HTTP APIs is API-level (`cors-configuration`); on REST
  APIs it is per-resource (mock OPTIONS method).** Missing
  `AllowMethods: [OPTIONS]` means preflight fails.

- **VPC link integrations require the NLB target group to be healthy.**
  The VPC link is transparent; always `describe-target-health`.

- **Access logging and execution logging are separate.** Access logs
  record every request; execution logs record API Gateway internals.
  Operators who "don't see logs" often enabled one but not the other.

### Step 1: Symptom entry

| Symptom | Branch |
|---|---|
| `403 Forbidden`, JWT denial | Step 2 — JWT Authorizer |
| `404 Not Found` / wrong route | Step 3 — Route matching |
| Browser CORS error | Step 4 — CORS |
| `502 Bad Gateway` from Lambda | Step 5 — Lambda proxy / Payload version |
| `502`/`504` after 29 seconds | Step 6 — Integration timeout |
| `429 Too Many Requests` | Step 7 — Throttling |
| Config changed but not live | Step 8 — Stage deployment |
| `502` from VPC link / private integration | Step 9 — VPC link |
| No logs despite traffic | Step 10 — Logging |
| None of the above | Step 11 — INSUFFICIENT_DATA |

### Step 2: JWT Authorizer — 403 Forbidden

```bash
aws apigatewayv2 get-authorizer --api-id <api-id> \
  --authorizer-id <id> --output json | \
  jq '{AuthorizerType, IdentitySource, JwtConfiguration}'
```

| Field | Effect |
|---|---|
| `IdentitySource` | Must match the client's header name. `$request.header.Authorization` expects `Authorization: Bearer <token>`. |
| `JwtConfiguration.Issuer` | Must match the token's `iss` claim exactly (including trailing slash). |
| `JwtConfiguration.Audience` | Must match the token's `aud` claim. Empty = any audience (insecure). |

Common failures: identity source header mismatch, issuer mismatch
(wrong Cognito pool), audience mismatch (wrong client ID).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: JWT_AUTHORIZER`. Fix: update
`IdentitySource`, `Issuer`, or `Audience`; create a deployment.

### Step 3: Route matching — 404 or wrong route handling

```bash
aws apigatewayv2 get-routes --api-id <api-id> --output json | \
  jq '.Items[] | {RouteKey, RouteId, Target, AuthorizerId}'
```

| Pattern | Cause |
|---|---|
| Route exists but returns 404 | Stage not deployed. Route is in config but not in the deployed snapshot. |
| `$default` catches traffic for `POST /orders` | Route key case mismatch, trailing slash, or route added after last deployment. |
| `ANY /{proxy+}` swallows everything (REST) | Catch-all proxy on REST API; resource tree needs explicit child resources. |
| Client sends `PUT` but route is `POST` | No match → `$default` or 404. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ROUTE_MATCHING` or
`ROUTE_PRIORITY_CATCHALL`. Fix: correct route key; deploy the stage.

### Step 4: CORS — browser preflight errors

```bash
# HTTP API: CORS is API-level
aws apigatewayv2 get-api --api-id <api-id> --output json | jq '.CorsConfiguration'
# REST API: CORS is per-resource (mock OPTIONS method)
aws apigateway get-method --rest-api-id <id> --resource-id <rid> \
  --http-method OPTIONS --output json
```

| Pattern | Cause |
|---|---|
| `AllowOrigins` missing the browser origin | Browser blocks the response. |
| `AllowMethods` missing `OPTIONS` | Preflight fails; browser never sends the actual request. |
| `AllowHeaders` missing `Content-Type` or `Authorization` | Preflight rejects declared headers. |
| `AllowCredentials: true` with `AllowOrigins: ["*"]` | Invalid per CORS spec. Use explicit origins. |
| REST API: no mock OPTIONS method | REST APIs require a per-resource OPTIONS method. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CORS_MISCONFIG`. Fix: update
`CorsConfiguration` (HTTP API) or add mock OPTIONS method (REST API).

### Step 5: Lambda proxy 502 — payload format version and response shape

```bash
aws apigatewayv2 get-integration --api-id <api-id> \
  --integration-id <id> --output json | \
  jq '{IntegrationType, IntegrationSubtype, PayloadFormatVersion}'
```

**5a: Payload format version mismatch.** `PayloadFormatVersion: 2.0`
may deliver `event.body` as base64 with `isBase64Encoded: true`. A
handler that does `JSON.parse(event.body)` without checking throws on
binary content. Fix: handle base64 decoding, or switch to 1.0.

**5b: Lambda response shape.** API Gateway expects:

```json
{"statusCode": 200, "headers": {...}, "body": "...", "isBase64Encoded": false}
```

Common shape failures: `statusCode` as string instead of integer;
`body` as object instead of string; `body` omitted on v2.0; unhandled
exception. All produce 502.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PAYLOAD_FORMAT_VERSION` or
`INTEGRATION_LAMBDA_PROXY`.

### Step 6: Integration timeout — 502 / 504 at 29 seconds

The 29-second cap is enforced regardless of the integration's timeout.

| Pattern | Cause |
|---|---|
| Lambda Timeout = 60s, API returns 502 at 29s | API Gateway gives up first. Lower Lambda to ≤ 29s or move async. |
| HTTP integration to slow backend | Backend genuinely takes > 29s. Redesign as async. |
| VPC link to NLB, backend slow | Same — move to async. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: INTEGRATION_TIMEOUT`.

### Step 7: Throttling — 429 Too Many Requests

```bash
aws apigatewayv2 get-stage --api-id <api-id> \
  --stage-name <stage> --output json | \
  jq '{DefaultRouteSettings, RouteSettings}'
```

| Pattern | Cause |
|---|---|
| `RateLimit`/`BurstLimit` too low | Raise on the stage or route. |
| Per-route throttling stricter than stage | Check `RouteSettings`. |
| Account-level throttling hit | Request quota increase. |
| WAF rate-based rule | Check WAF web ACL on the API. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: THROTTLING_BURST`.

### Step 8: Stage deployment — changes not live

```bash
aws apigatewayv2 get-stage --api-id <api-id> \
  --stage-name <stage> --output json | jq '{AutoDeploy, LastDeploymentStatus}'
```

| Pattern | Cause |
|---|---|
| `AutoDeploy: false` | Requires manual `create-deployment`. |
| `AutoDeploy: true` but `LastDeploymentStatus: FAILED` | Auto-deploy failed. Check error details. |
| REST API: no deployment after change | REST APIs ALWAYS require manual deployment. |

```bash
aws apigatewayv2 create-deployment --api-id <api-id> --stage-name <stage>
```

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: STAGE_DEPLOYMENT`.

### Step 9: VPC link — private integration 502

```bash
aws apigatewayv2 get-vpc-links --output json | \
  jq '.Items[] | {VpcLinkId, Name, SubnetIds, SecurityGroupIds}'
aws elbv2 describe-target-health --target-group-arn <arn> --output json
```

| Pattern | Cause |
|---|---|
| NLB target group zero healthy targets | Backend down or failing health checks. |
| VPC link SG blocks NLB traffic | Update SG rules. |
| Wrong `ConnectionId` on integration | Points to wrong VPC link. |
| NLB in different VPC than VPC link subnets | Subnets must be in same VPC as NLB. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: VPCLINK_CONNECTIVITY`.

### Step 10: Logging — no logs despite traffic

```bash
aws apigatewayv2 get-stage --api-id <api-id> \
  --stage-name <stage> --output json | \
  jq '{AccessLogSettings, DefaultRouteSettings: .DefaultRouteSettings.LoggingLevel}'
```

| Pattern | Cause |
|---|---|
| `AccessLogSettings` not configured | No access logs. Configure destination ARN and format. |
| `LoggingLevel` not set | Execution logs not emitted. Set `INFO` or `ERROR`. |
| IAM role for CloudWatch Logs missing | API Gateway needs `AmazonAPIGatewayPushToCloudWatchLogs`. |
| Wrong log group name | Check `/aws/apigateway/<api-id>/<stage>`. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: LOGGING_MISCONFIG`.

### Step 11: INSUFFICIENT_DATA

If critical configuration is missing (integration ID, authorizer ID,
VPC link ID, stage name, API type), emit INSUFFICIENT_DATA with the
exact missing fields and the next probe to run once info is available.

## Output format

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
  - <failing probe — command and output confirming the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <api-id> in <region>. Proceed?
  (yes/no)"
```

### Worked example — Payload format version 2.0 base64 body

```text
TARGET: api abc1234 / POST /orders / stage $default
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: Integration PayloadFormatVersion is 2.0; the Lambda handler
  reads event.body as raw JSON without checking isBase64Encoded. POST
  bodies with binary content arrive base64-encoded and JSON.parse
  throws, causing 502 Bad Gateway (Step 5a).
LAYER: PAYLOAD_FORMAT_VERSION
EVIDENCE:
  - Symptom: POST /orders returns 502 when body > 1 KB; GET succeeds.
  - Probe: aws apigatewayv2 get-integration returns PayloadFormatVersion: "2.0".
  - Probe: Lambda logs show "SyntaxError: Unexpected token in JSON" at
    JSON.parse(event.body) with isBase64Encoded: true.
  - Passing: AutoDeploy true; JWT audience matches; CORS allows origin.
REMEDIATION:
  1. Update handler to check isBase64Encoded:
     if (event.isBase64Encoded) {
       event.body = Buffer.from(event.body, 'base64').toString('utf-8');
     }
  2. Redeploy Lambda; verify POST /orders succeeds with 2 KB body.
  3. Alternative: switch to PayloadFormatVersion 1.0:
     aws apigatewayv2 update-integration --api-id abc1234 \
       --integration-id int-xyz --payload-format-version 1.0
CONFIRM: Before updating, emit: "CONFIRM: About to update integration
  PayloadFormatVersion on api abc1234. Proceed? (yes/no)"
```

### Worked example — INSUFFICIENT_DATA

```text
TARGET: api abc1234 / unknown route
VERDICT: INSUFFICIENT_DATA
REASON: Symptom is 502 on POST /webhook, but integration ID,
  PayloadFormatVersion, and VPC link configuration are not provided.
  Cannot distinguish payload format mismatch, Lambda response shape
  error, or VPC link backend failure.
LAYER: UNKNOWN
EVIDENCE:
  - Symptom: POST /webhook returns 502 intermittently.
  - Missing: IntegrationId, PayloadFormatVersion, ConnectionType,
    VPC link ID, NLB target group ARN.
  - Missing: Execution logs or Lambda logs for a failing request.
REMEDIATION: Provide: (1) integration config from get-integration,
  (2) VPC link details if private integration, (3) execution logs or
  Lambda logs for a failing request, (4) confirm intermittent vs
  consistent 502.
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe matching
  the symptom. A "process of elimination" erodes operator trust.

- NEVER debug an HTTP API (apigatewayv2) with REST API (apigateway)
  tooling. The CLIs, config models, and payload formats differ.

- NEVER assume PayloadFormatVersion is 1.0. HTTP API Lambda integrations
  default to 2.0, which base64-encodes binary bodies. Always check.

- NEVER recommend raising the Lambda timeout past 29 seconds for an
  API-Gateway-facing integration. API Gateway has a hard 29-second cap.

- NEVER configure `AllowOrigins: ["*"]` with `AllowCredentials: true`.
  The CORS spec forbids it. Use explicit origins.

- NEVER assume a stage is auto-deployed. HTTP API stages with
  `AutoDeploy: false` and ALL REST API stages require manual
  `create-deployment`.

- NEVER conclude "the route does not exist" without checking the
  deployed snapshot. A route may exist in config but not in the stage.

- NEVER conflate access logging with execution logging. They are
  separate features recording different data.

- NEVER assume a VPC link failure is a VPC link config issue. The VPC
  link is transparent; check NLB target group health first.

- NEVER change `PayloadFormatVersion` without verifying the handler
  expects the new format. Test in non-prod first.

- NEVER leave `JwtConfiguration.Audience` empty in production. An empty
  audience accepts any token from the issuer — a security risk.

- NEVER trust a browser CORS error at face value. The browser reports
  "No Access-Control-Allow-Origin" for ANY failed cross-origin request,
  including 403s and 502s. Check the actual HTTP response first.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before `update-authorizer`,
  `update-integration`, `create-deployment`, `update-route`, or
  `update-stage`, emit and await operator approval.

- **Read-only first.** Every probe is read-only (`get-*`,
  `filter-log-events`, `describe-target-health`).

- **`create-deployment`** is the user-visible cutover for REST APIs.
  Confirm the stage name before deploying.

- **`update-authorizer`** with new `Audience`/`Issuer` can lock out all
  clients. Verify against a sample decoded token first.

- **`update-integration --payload-format-version`** changes the event
  shape. Test in non-prod first.

## Expert heuristic

Three heuristics separate a senior API Gateway engineer from a
generalist:

### Heuristic 1: Payload format version determines body encoding

- **v2.0** → body may be base64-encoded (`isBase64Encoded: true`),
  headers are flat, `requestContext` is simplified. Handler must check
  and decode.
- **v1.0** → body is a raw string, headers are multi-value,
  `requestContext` is the REST API shape.
- The silent break: a handler migrated from REST API (v1.0) to HTTP
  API (v2.0) fails on POST bodies because `JSON.parse(event.body)`
  encounters a base64 string. The error appears as 502 Bad Gateway.

### Heuristic 2: JWT claim mapping is issuer + audience + identity source

- `Issuer` must match the token's `iss` exactly (scheme + trailing
  slash). Cognito issuers are
  `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>`.
- `Audience` must match at least one value in the token's `aud` claim.
  Empty `Audience` accepts any audience (insecure).
- `IdentitySource` maps the request header to the token. A mismatch
  means the authorizer receives an empty string and denies everything.

### Heuristic 3: Route priority evaluation order

- Exact match first (`GET /orders`), then greedy/variable
  (`GET /orders/{id}`), then `$default` (catch-all).
- `$default` masks undeployed routes, mis-keyed routes (case
  sensitivity, trailing slash), and missing methods.
- Diagnostic order: (1) check route exists in config, (2) check stage
  was deployed, (3) check route key for case/slash/method mismatch.

## Configuration dependency graph

```
Client Request
    │
    ▼
┌──────────────────────────────────┐
│  Stage (auto-deploy?)            │── Step 8: STAGE_DEPLOYMENT
│    │                             │
│    ▼                             │
│  Route Matching                  │── Step 3: ROUTE_MATCHING
│  (exact → greedy → $default)     │   ROUTE_PRIORITY_CATCHALL
│    │                             │
│    ▼                             │
│  Authorizer (JWT?)               │── Step 2: JWT_AUTHORIZER
│  (issuer, audience, id source)   │
│    │                             │
│    ▼                             │
│  CORS Check (preflight OPTIONS)  │── Step 4: CORS_MISCONFIG
│    │                             │
│    ▼                             │
│  Throttling (rate, burst)        │── Step 7: THROTTLING_BURST
│    │                             │
│    ▼                             │
│  Integration                     │── Step 5: PAYLOAD_FORMAT_VERSION
│  ┌─ Lambda Proxy (1.0 vs 2.0) ─┐ │   INTEGRATION_LAMBDA_PROXY
│  └─────────────────────────────┘ │── Step 6: INTEGRATION_TIMEOUT
│  ┌─ VPC Link → NLB → TG ───────┐ │── Step 9: VPCLINK_CONNECTIVITY
│  └─────────────────────────────┘ │
│    │                             │
│    ▼                             │
│  Logging (access vs execution)   │── Step 10: LOGGING_MISCONFIG
└──────────────────────────────────┘
```

## Domain

AWS CloudOps / Application Integration, API Gateway HTTP API
Diagnostics, Routing, Authorisation, Integration Mapping, and Private
Connectivity.

## AWS documentation

- **API Gateway HTTP API Developer Guide** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html
- **Payload format versions for Lambda proxy integration** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html
- **JWT authorizers for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html
- **CORS for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-cors.html
- **VPC links for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vpc-links.html
- **Stage management for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-stages.html
- **Throttling for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-throttling.html
- **Access logging for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-logging.html
