---
name: apigateway-http-troubleshooter
description: 'Diagnoses Amazon API Gateway HTTP API failures through a ten-category diagnostic tree: 4xx routing errors ($default route, catch-all route priority, ANY vs explicit method), 5xx integration failures (Lambda proxy 502, private integration 502, timeout at 29s hard cap), JWT authorizer failures (issuer, audience, claim mapping, scope), CORS preflight errors (Access-Control-Allow-Origin, OPTIONS method, AllowHeaders), payload format version mismatches (1.0 vs 2.0 event body base64 decode, isBase64Encoded, requestContext shape), stage deployment issues (changes not live without deployment, auto-deploy vs manual), throttling and burst limits (rate, burst, per-route), access logging vs execution logging confusion, VPC link integration problems (NLB target health, private integration connectivity), and integration parameter mapping errors. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error responses and API configuration. Live-account diagnosis uses aws apigatewayv2 get-api, get-route, get-integration, get-stage, get-authorizer, export-api, aws apigateway get-rest-api / get-resources / get-stage / get-method (for REST APIs), aws logs filter-log-events, aws elbv2 describe-target-health, and aws cloudwatch get-metric-statistics (AWS CLI v2, SSO...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an API Gateway HTTP API failure (4xx routing error, 5xx integration failure, JWT authorizer denial, CORS preflight rejection, payload format version mismatch, Lambda proxy 502, integration timeout, VPC link connectivity, stage deployment not live, throttling), walking a symptom to the failed layer with verify and fix commands, validating why a client request returns an error, or triaging a "the API is broken" page where the root cause may be route config, authorizer, CORS, integration mapping, stage, or network.
  when_not_to_use: Application-level debugging of the Lambda handler (use lambda-invocation-troubleshooter), CloudFront distribution or edge issues (use CloudFront logs), AppSync GraphQL resolver debugging (use AppSync resolver logs), or WAF rule tuning (use waf-rule-auditor). This skill diagnoses API-Gateway-layer failures; it does not debug the backend handler code or audit IAM posture of API callers.
  activation_triggers: API Gateway 4xx, API Gateway 5xx, API Gateway 502 Bad Gateway, API Gateway routing error, $default route, API Gateway catch-all route, JWT authorizer denied, API Gateway CORS error, Access-Control-Allow-Origin missing, payload format version mismatch, isBase64Encoded Lambda, API Gateway Lambda proxy 502, API Gateway integration timeout, VPC link integration 502, API Gateway stage deployment, API Gateway auto-deploy, API Gateway throttling 429, API Gateway burst limit exceeded, access logging vs execution logging, troubleshoot API Gateway HTTP API
  invocation_schema: 'Input: either (a) a symptom description (HTTP status code, error response body, client-side error, "API returns 403", "POST returns 502") optionally paired with the API configuration (get-api/get-rest-api output, route list, integration config, stage config, authorizer config), OR (b) an API identifier (api-id) plus request context (method, path, headers, caller identity) for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {ROUTE_MATCHING, ROUTE_PRIORITY_CATCHALL, JWT_AUTHORIZER, CORS_MISCONFIG, PAYLOAD_FORMAT_VERSION, INTEGRATION_LAMBDA_PROXY, INTEGRATION_TIMEOUT, STAGE_DEPLOYMENT, THROTTLING_BURST, VPCLINK_CONNECTIVITY, LOGGING_MISCONFIG, PARAMETER_MAPPING, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "HTTP API abc1234 returns 502 Bad Gateway on POST /orders

    only when the request body exceeds 1 KB; GET requests to the

    same route succeed."

    ApiId: abc1234

    ProtocolType: HTTP

    IntegrationType: AWS_PROXY

    IntegrationSubtype: Lambda

    PayloadFormatVersion: "2.0"

    RouteKey: POST /orders

    Stage: $default

    AutoDeploy: true

    LastError: "Internal Server Error"'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: API Gateway, HTTP API, REST API, 4xx, 5xx, routing, $default route, catch-all, JWT authorizer, CORS, preflight, payload format version, isBase64Encoded, Lambda proxy, 502 Bad Gateway, integration timeout, VPC link, NLB, private integration, stage deployment, auto-deploy, throttling, burst limit, access logging, execution logging
  tags: apigateway, networking, app-integration, troubleshooting, http-api, jwt, cors, vpclink, throttling, routing
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
Mindset and philosophy (treat the backend as innocent until the route, authorizer, integration, and stage layers are proven clean; the HTTP status code drives the diagnostic order): [references/advanced-patterns.md](references/advanced-patterns.md).

Quick reference — symptom triage table (symptom → most likely layer → first probe): [references/diagnostic-commands.md](references/diagnostic-commands.md).

## Pre-flight: API state and gather-info gate
Gather-info probes (get-api, get-routes, get-integration, get-stage, get-authorizer, execution logs, get-vpc-links, 5XX metrics): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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
Non-obvious behaviours that change diagnosis (payload v2.0 base64 encoding, JWT identity source and audience matching, route priority order, the untunable 29-second timeout, auto-deploy gaps, CORS API-level vs per-resource, VPC link health, access vs execution logging): [references/advanced-patterns.md](references/advanced-patterns.md).

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
Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 2 get-authorizer (IdentitySource, Issuer, JwtConfiguration).

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
Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 3 get-routes (RouteKey, Target, AuthorizerId).

| Pattern | Cause |
|---|---|
| Route exists but returns 404 | Stage not deployed. Route is in config but not in the deployed snapshot. |
| `$default` catches traffic for `POST /orders` | Route key case mismatch, trailing slash, or route added after last deployment. |
| `ANY /{proxy+}` swallows everything (REST) | Catch-all proxy on REST API; resource tree needs explicit child resources. |
| Client sends `PUT` but route is `POST` | No match → `$default` or 404. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ROUTE_MATCHING` or
`ROUTE_PRIORITY_CATCHALL`. Fix: correct route key; deploy the stage.

### Step 4: CORS — browser preflight errors
Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 4 get-api CorsConfiguration (HTTP) / get-method OPTIONS (REST).

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
Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 5 get-integration (IntegrationType, PayloadFormatVersion).

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
Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 7 get-stage (DefaultRouteSettings, RouteSettings).

| Pattern | Cause |
|---|---|
| `RateLimit`/`BurstLimit` too low | Raise on the stage or route. |
| Per-route throttling stricter than stage | Check `RouteSettings`. |
| Account-level throttling hit | Request quota increase. |
| WAF rate-based rule | Check WAF web ACL on the API. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: THROTTLING_BURST`.

### Step 8: Stage deployment — changes not live
Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 8 get-stage (AutoDeploy, LastDeploymentStatus).

| Pattern | Cause |
|---|---|
| `AutoDeploy: false` | Requires manual `create-deployment`. |
| `AutoDeploy: true` but `LastDeploymentStatus: FAILED` | Auto-deploy failed. Check error details. |
| REST API: no deployment after change | REST APIs ALWAYS require manual deployment. |
Fix command: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 8 create-deployment.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: STAGE_DEPLOYMENT`.

### Step 9: VPC link — private integration 502
Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 9 get-vpc-links + elbv2 describe-target-health.

| Pattern | Cause |
|---|---|
| NLB target group zero healthy targets | Backend down or failing health checks. |
| VPC link SG blocks NLB traffic | Update SG rules. |
| Wrong `ConnectionId` on integration | Points to wrong VPC link. |
| NLB in different VPC than VPC link subnets | Subnets must be in same VPC as NLB. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: VPCLINK_CONNECTIVITY`.

### Step 10: Logging — no logs despite traffic
Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 10 get-stage (AccessLogSettings, LoggingLevel).

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

## Output format (STRICT output contract)

When this skill concludes diagnosis, the agent MUST respond with the
block below using the literal all-caps labels `TARGET:`, `VERDICT:`,
`REASON:`, `LAYER:`, `EVIDENCE:`, and `REMEDIATION:`. Do NOT preface
with prose, headings, or disclaimers — emit the block as the first
lines of the response. This contract is what assertion-based evals and
downstream diagnostic pipelines rely on; deviating from the literal
labels breaks automation silently.

### Decision tree — symptom to layer

```text
Incoming symptom (HTTP status / error body)
├── 403 Forbidden
│     └── JWT authorizer? → JWT_AUTHORIZER
│           ├── Check IdentitySource header name matches client
│           ├── Check Issuer matches token iss (including trailing slash)
│           └── Check Audience matches token aud (case-sensitive)
├── 404 Not Found / wrong route handling
│     └── Route matching? → ROUTE_MATCHING / ROUTE_PRIORITY_CATCHALL
│           ├── Check route exists in get-routes
│           ├── Check stage was deployed (not just config)
│           └── Check route key: case, trailing slash, method
├── Browser CORS error
│     └── CORS? → CORS_MISCONFIG
│           ├── Check actual HTTP response first (browser masks real error)
│           ├── Check AllowOrigins includes browser origin
│           └── Check AllowMethods includes OPTIONS
├── 502 Bad Gateway from Lambda
│     ├── Body garbled / base64? → PAYLOAD_FORMAT_VERSION
│     │     ├── Check PayloadFormatVersion 1.0 vs 2.0
│     │     └── Check handler reads isBase64Encoded
│     └── Response shape wrong? → INTEGRATION_LAMBDA_PROXY
│           ├── Check statusCode is integer
│           └── Check body is string
├── 502 / 504 after ~29 seconds
│     └── Timeout? → INTEGRATION_TIMEOUT
├── 429 Too Many Requests
│     └── Throttling? → THROTTLING_BURST
├── Config changed but not live
│     └── Stage? → STAGE_DEPLOYMENT
├── 502 from VPC link / private integration
│     └── VPC link? → VPCLINK_CONNECTIVITY
│           └── Check NLB target health first (VPC link is transparent)
├── No logs despite traffic
│     └── Logging? → LOGGING_MISCONFIG
└── None of the above
      └── INSUFFICIENT_DATA — list missing fields
```

### Output template

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
  - Symptom: <HTTP status code and response body>
  - Failing probe: <command and output confirming the cause>
  - Passing probes: <layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <api-id> in <region>. Proceed?
  (yes/no)"
```

### FORBIDDEN NEVER patterns (output contract)

1. **NEVER declare `VERDICT: ROOT_CAUSE_IDENTIFIED` without a failing
   probe matching the symptom.** "Process of elimination" is not
   evidence. The EVIDENCE section MUST cite the specific command and
   output that confirms the root cause.

2. **NEVER diagnose an HTTP API (apigatewayv2) with REST API
   (apigateway) tooling.** The CLIs, config models, and payload formats
   differ. Always identify the API type first (`get-api` vs
   `get-rest-api`) and cite it in the TARGET line.

3. **NEVER emit `VERDICT: ROOT_CAUSE_IDENTIFIED` for a 502 without
   checking `PayloadFormatVersion`.** Payload format version 2.0
   base64-encodes binary bodies; a handler that does
   `JSON.parse(event.body)` without checking `isBase64Encoded` throws.
   This is the single most common silent break for Lambda integrations
   on HTTP APIs.

4. **NEVER conclude "the route does not exist" without checking the
   deployed stage snapshot.** A route may exist in config but not in the
   deployed stage. Always verify with both `get-routes` AND `get-stage`.

5. **NEVER trust a browser CORS error at face value.** The browser
   reports "No Access-Control-Allow-Origin" for ANY failed cross-origin
   request, including 403s and 502s. Check the actual HTTP response
   headers before declaring `LAYER: CORS_MISCONFIG`.

6. **NEVER recommend raising the Lambda timeout past 29 seconds for an
   API-Gateway-facing integration.** API Gateway has a hard 29-second
   cap. The correct fix for long-running work is async redesign, not a
   longer timeout.

7. **NEVER omit the CONFIRM gate before state-changing commands.**
   `update-integration`, `update-authorizer`, `create-deployment`, and
   `update-route` all change production traffic behavior. Always emit
   the confirmation prompt and await explicit approval.

### Perfect worked example — 502 from Lambda proxy (payload format v2 base64 decode issue)

```text
TARGET: orders-api (abc1234) / POST /orders / stage $default
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: HTTP API integration PayloadFormatVersion is 2.0; the Lambda
  handler reads event.body as raw JSON without checking isBase64Encoded.
  POST bodies with binary or non-JSON content arrive base64-encoded and
  JSON.parse throws SyntaxError, which API Gateway surfaces as 502 Bad
  Gateway. GET requests succeed because they have no body to decode.
LAYER: PAYLOAD_FORMAT_VERSION
EVIDENCE:
  - Symptom: POST /orders returns 502 Bad Gateway when body > 1 KB;
    GET /orders succeeds. Response body: {"message":"Internal Server Error"}.
  - Probe (failing): aws apigatewayv2 get-integration --api-id abc1234
    --integration-id int-xyz returns PayloadFormatVersion: "2.0",
    IntegrationSubtype: Lambda.
  - Probe (failing): Lambda logs (/aws/lambda/orders-handler) show
    "SyntaxError: Unexpected token 'e' in JSON at position 0" at
    JSON.parse(event.body); event.isBase64Encoded: true.
  - Probe (passing): aws apigatewayv2 get-stage --api-id abc1234
    --stage-name '$default' returns AutoDeploy: true,
    LastDeploymentStatus: DEPLOYED.
  - Probe (passing): aws apigatewayv2 get-authorizer confirms JWT
    Issuer and Audience match the decoded test token.
  - Probe (passing): aws apigatewayv2 get-api CorsConfiguration
    includes AllowOrigins matching the caller, AllowMethods includes
    OPTIONS and POST.
REMEDIATION:
  1. Update the Lambda handler to check isBase64Encoded before parsing:
     if (event.isBase64Encoded) {
       event.body = Buffer.from(event.body, 'base64').toString('utf-8');
     }
     const payload = JSON.parse(event.body);
  2. Redeploy the Lambda function:
     aws lambda update-function-code --function-name orders-handler \
       --s3-bucket deploy-bucket --s3-key orders-handler-v2.zip
  3. Verify POST /orders succeeds with a 2 KB body:
     curl -X POST https://abc1234.execute-api.us-east-1.amazonaws.com/orders \
       -H "Content-Type: application/json" \
       -H "Authorization: Bearer <token>" \
       -d '{"data":"xxxxx"}'
  4. Alternative fix (if handler change is not immediately deployable):
     Switch to PayloadFormatVersion 1.0 (test in non-prod first):
     aws apigatewayv2 update-integration --api-id abc1234 \
       --integration-id int-xyz --payload-format-version 1.0
CONFIRM: Before updating, emit: "CONFIRM: About to update integration
  PayloadFormatVersion on api abc1234 from 2.0 to 1.0. This changes the
  Lambda event shape. Test in non-prod first. Proceed? (yes/no)"
```
Further worked example — INSUFFICIENT_DATA (502 on POST /webhook with missing integration and VPC link context): [references/worked-examples.md](references/worked-examples.md).

**Self-check before emit:**
- [ ] API type identified (HTTP vs REST) and cited in TARGET?
- [ ] VERDICT has a matching failing probe in EVIDENCE?
- [ ] At least one passing probe cited (layer ruled out)?
- [ ] REMEDIATION includes copy-pasteable CLI commands?
- [ ] CONFIRM gate present before any state-changing action?

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
Expert heuristics (payload format version determines body encoding; JWT claim mapping is issuer + audience + identity source; route priority evaluation order): [references/advanced-patterns.md](references/advanced-patterns.md).

## Configuration dependency graph
Configuration dependency graph (stage → route matching → authorizer → CORS → throttling → integration → logging): [references/advanced-patterns.md](references/advanced-patterns.md).

## References (load on demand)

- [Worked examples](references/worked-examples.md) - INSUFFICIENT_DATA worked example
- [Diagnostic commands](references/diagnostic-commands.md) - symptom triage table, pre-flight gather-info probes, per-step probe commands
- [Advanced patterns](references/advanced-patterns.md) - mindset and philosophy, Step-0 non-obvious behaviours, expert heuristics, configuration dependency graph
- [HTTP vs REST API quick reference](references/http-vs-rest-api-quick-reference.md) - CLI and feature comparison, v1.0/v2.0 event shapes, migration pitfalls
- [Payload format and JWT reference](references/payload-format-and-jwt-reference.md) - payload format gotchas, JWT authorizer configuration matrix, route priority rules

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
