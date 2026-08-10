---
name: apigateway-5xx-troubleshooter
description: >-
  Diagnoses Amazon API Gateway 5xx errors (500 InternalServerError, 502
  BadGateway, 503 ServiceUnavailable, 504 Timeout) through a systematic
  diagnostic tree covering Lambda proxy response format errors, Lambda
  runtime crashes, HTTP backend invalid responses, VPC Link target health,
  throttling at stage/concurrency/usage-plan layers, integration timeout
  mismatches, and rare internal failures. Walks symptoms to root cause with
  CloudWatch metrics (5xxError, Latency), access logs (integrationErrorMessage,
  responseLatency), CloudTrail Invoke API calls, and Lambda LogError scans.
  Emits ROOT_CAUSE_FOUND with the specific failure layer or ESCALATE for
  AWS-side incidents. Use when API Gateway returns 5xx errors, Lambda proxy
  format errors, integration timeouts, or throttled requests.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline symptom classification works from pasted error strings
  and stage/integration metadata. Live-account diagnosis uses aws apigateway
  get-stage, get-resources, get-method, get-integration, aws apigatewayv2
  get-stage, aws lambda get-function-configuration, aws logs filter-log-events
  (Lambda LogError scan), aws cloudwatch get-metric-statistics, and aws
  cloudtrail lookup-events (AWS CLI v2, SSO or key-based credentials).
keywords:
  - API Gateway
  - 5xx
  - 500
  - 502
  - 503
  - 504
  - BadGateway
  - ServiceUnavailable
  - GatewayTimeout
  - InternalServerError
  - Lambda proxy
  - integration timeout
  - throttling
  - rate limit
  - burst limit
  - concurrency
  - usage plan
  - VPC Link
  - mapping template
  - CloudWatch metrics
  - access logs
  - CloudTrail
  - troubleshooting
tags: [apigateway, app-integration, troubleshooting, 5xx, lambda, throttle, timeout, cloudwatch]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: App Integration
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Diagnosing an API Gateway 5xx error (500, 502, 503, 504), walking a
    symptom to the failed integration layer with verify and fix commands,
    validating a Lambda proxy response format, diagnosing integration
    timeouts, identifying stage/usage-plan/concurrency throttling, or
    triaging a "the API is returning 5xx" page where the root cause may be
    Lambda, the HTTP backend, VPC Link health, throttling, or timeout
    configuration — not necessarily API Gateway itself.
  when_not_to_use: >-
    Configuration posture audits (use apigateway-resource-policy-auditor),
    authoring resource policies, deploying new APIs (use the deploy task
    type), Lambda function code debugging beyond the integration contract,
    or 4xx error diagnosis (4xx is a client/auth problem, not a 5xx backend
    problem).
  activation_triggers:
    - "API Gateway 5xx error"
    - "API Gateway 502 BadGateway"
    - "API Gateway 504 timeout"
    - "API Gateway 503 throttled"
    - "API Gateway 500 InternalServerError"
    - "Lambda proxy malformed response"
    - "integration timed out"
    - "Execution failed due to a timeout error"
    - "Type Error in Lambda"
    - "Runtime.LogError"
    - "stage throttling exceeded"
    - "Lambda concurrent executions exceeded"
    - "API Gateway access logs 5xx"
    - "troubleshoot API Gateway"
  invocation_schema: >-
    Input: either (a) a symptom description (error code 500/502/503/504,
    observed latency pattern, recent deployment), optionally paired with
    the API/stage metadata (get-rest-apis/get-stage output, integration
    type, Lambda function configuration), OR (b) a REST API id + stage
    name for live-account diagnosis. Output: a deterministic
    TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT
    ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and LAYER ∈
    {BACKEND_LAMBDA_ERROR, BACKEND_RESPONSE_FORMAT, BACKEND_HTTP_INVALID,
    BACKEND_VPC_LINK, BACKEND_MAPPING_TEMPLATE, TIMEOUT_LAMBDA,
    TIMEOUT_HTTP, TIMEOUT_MISMATCH, THROTTLE_STAGE, THROTTLE_CONCURRENCY,
    THROTTLE_USAGE_PLAN, PAYLOAD_TOO_LARGE, INTERNAL_ERROR, UNKNOWN}.
---

# API Gateway 5xx Troubleshooter

## Quick start

- **Error code → layer map (first plausible match drives the first probe):**
  502 → BACKEND_LAMBDA_ERROR / BACKEND_RESPONSE_FORMAT /
  BACKEND_HTTP_INVALID / BACKEND_VPC_LINK / BACKEND_MAPPING_TEMPLATE;
  504 → TIMEOUT_LAMBDA / TIMEOUT_HTTP / TIMEOUT_MISMATCH;
  503 → THROTTLE_STAGE / THROTTLE_CONCURRENCY / THROTTLE_USAGE_PLAN;
  500 → INTERNAL_ERROR (rare — check AWS Health Dashboard).
- **Always verify with a probe, never guess.** Each layer has a single
  command (or log pattern) that proves or disproves it. A ROOT_CAUSE_FOUND
  verdict requires positive evidence — a failing probe that matches the
  symptom — not "must be the Lambda."
- **Order matters: classify the code before probing.** A 502 means the
  backend responded invalidly; a 504 means it did not respond in time. Do
  NOT chase Lambda logs for a 504 that is actually a slow HTTP integration.
- **ESCALATE for AWS-side incidents.** A sustained 500 with no recent
  deployment, no throttling, and clean backends is an AWS-side event —
  surface the Health Dashboard link and open a Support case.

## Mindset

A "5xx from API Gateway" page is usually a backend or configuration incident
wearing an API Gateway costume. API Gateway itself is rarely the cause —
it is the messenger. The broken thing is the Lambda function, the HTTP
backend, the VPC Link target, the throttling policy, or the timeout
configuration. Treat API Gateway as a relay until the backend response,
timing, and throttle layers are proven clean.

## Philosophy

Four behaviours separate a senior API Gateway engineer from a generalist:

- **The 5xx code tells you WHERE the failure happened.** A 502 means API
  Gateway reached the backend but the backend returned something invalid
  (Lambda proxy format error, HTTP backend malformed response, VPC Link
  unhealthy target). A 504 means the backend did not respond within the
  integration timeout (Lambda exceeded 29s, HTTP backend too slow). A 503
  means API Gateway or Lambda refused the request before reaching the
  backend (throttling). A 500 means API Gateway itself failed. Routing
  the code to the wrong layer is the #1 source of wasted cycles.

- **Lambda proxy response format is non-negotiable.** A REST API Lambda
  proxy integration REQUIRES the function to return
  `{statusCode, body, headers}`. A function returning a bare string, a
  Promise reject, or an Error object produces a 502 with
  `Execution failed due to configuration: Malformed Lambda proxy response`.
  This is the single most common 502 root cause. HTTP APIs (v2) have the
  same format requirement but a slightly different error string.

- **Integration timeout (29s) is shorter than Lambda timeout (15 min).**
  A Lambda function configured with a 60s timeout behind a REST API will
  be killed at 29s by API Gateway's integration timeout — the function
  continues running (and billing) for up to 60s, but the client receives
  a 504 at 29s. The mismatch is invisible in the Lambda console (the
  function succeeds) but visible in API Gateway access logs
  (`integrationErrorMessage: Execution failed due to a timeout error`).

- **Throttling has three layers.** Stage-level (rate/burst on the stage),
  usage-plan-level (per-API-key rate/burst/quota), and account-level Lambda
  concurrency (reserved + unreserved). A 503 with no backend error and no
  timeout is almost always one of these three. The 5xxError CloudWatch
  metric spiking during traffic peaks, with Count also spiking, is the
  signature of throttling — not backend failure.

## Quick navigation

| If the symptom is... | Go to | First probe |
|---|---|---|
| 502 with `Malformed Lambda proxy response` | Step 2b | Lambda logs for the response object shape |
| 502 with Lambda `Runtime.LogError` / `Task timed out` | Step 2a | `aws logs filter-log-events` on the Lambda log group |
| 502 with HTTP backend (EC2/ALB) | Step 2c | Backend health check + direct curl from a test host |
| 502 with VPC Link integration | Step 2d | `aws elbv2 describe-target-health` for the NLB |
| 502 with mapping template error | Step 2e | CloudWatch Logs for `Mapping template` errors |
| 504 with Lambda timing out | Step 3a | Lambda Duration vs API Gateway Latency metrics |
| 504 with Lambda timeout > 29s integration | Step 3c | `aws lambda get-function-configuration` Timeout vs integration |
| 504 with HTTP backend slow | Step 3b | Backend response time; ALB target_processing_time |
| 503 with Count and 5xxError both spiking | Step 4 | CloudWatch Throttle metric + get-stage throttling |
| 500 sustained, no recent change | Step 5 | AWS Health Dashboard — ESCALATE |
| Need the metrics and access-log format | Reference | `references/error-codes-and-metrics.md` |

## Pre-flight: API type and gather-info gate

Before running code-specific probes, gather the canonical stage and
integration metadata. Misidentifying the API type (REST vs HTTP) or the
integration type (Lambda proxy vs non-proxy) produces false root causes.

### Account-wide pre-flight commands

```bash
# 1. REST API (v1) — stage config (throttling, deploymentId, access logs)
aws apigateway get-stage --rest-api-id <id> --stage-name <stage> --output json

# 2. HTTP API (v2) — stage config (throttling, route settings)
aws apigatewayv2 get-stage --api-id <id> --stage-name <stage> --output json

# 3. Integration type and timeout (REST)
aws apigateway get-resources --rest-api-id <id> --output json | \
  jq '.items[].resourceMethods'
aws apigateway get-integration --rest-api-id <id> --resource-id <rid> \
  --http-method <verb> --output json

# 4. Integration type and timeout (HTTP API v2)
aws apigatewayv2 get-integrations --api-id <id> --output json

# 5. Lambda function configuration (timeout, memory, runtime)
aws lambda get-function-configuration --function-name <fn> --output json

# 6. CloudWatch metrics — 5xxError, 4xxError, Count, Latency (per stage)
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value=<api> Name=Stage,Value=<stage> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum,Average --output json

# 7. AWS Health (regional events for API Gateway or Lambda)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

### API-type short-circuit

| Attribute | Value | Effect on diagnosis |
|---|---|---|
| `protocolType` | `REST` (v1) | Integration timeout is **29 seconds** (hard limit). Lambda proxy must return `{statusCode, body, headers}`. Supports usage plans, API keys, resource policies. Full diagnostic applies. |
| `protocolType` | `HTTP` (v2) | Integration timeout is **30 seconds**. Lambda proxy must return `{statusCode, body, headers}` (same format, different error string). No resource policies. JWT authorizers or IAM auth only. |
| Integration `type` | `AWS_PROXY` (Lambda proxy) | Lambda returns the response directly — format must match the proxy contract. Most 502s on this integration are BACKEND_RESPONSE_FORMAT. |
| Integration `type` | `AWS` (non-proxy Lambda) | API Gateway applies a mapping template to the Lambda response. 502s here are BACKEND_MAPPING_TEMPLATE. |
| Integration `type` | `HTTP` / `HTTP_PROXY` | Backend is an HTTP endpoint (EC2, ALB, on-prem). 502s are BACKEND_HTTP_INVALID. |
| Integration `type` | `VPC_LINK` | Backend is via a VPC Link to an NLB. 502s are BACKEND_VPC_LINK. |

If the input is malformed (missing API id, missing stage name, ambiguous
error code), emit:

```text
TARGET: <api-id/stage or unknown>
VERDICT: NEED_MORE_INFO
REASON: Input is missing required context — at minimum the 5xx error code
  (500/502/503/504), the API id, the stage name, and the integration type.
  Cannot drive a diagnostic tree without the error-code layer.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact 5xx error code from
  the client or access log, (2) the API id and stage name, (3) the
  integration type (Lambda proxy, HTTP, VPC Link), and (4) for live
  diagnosis, the time window of the failure.
```

## Process — Diagnostic decision tree (apply in error-code order)

The diagnostic tree is error-code-driven. Pick the entry point based on the
observed 5xx code, then walk the layer-specific probes in order. Each layer
ends with either a positive root-cause confirmation (failing probe that
matches the symptom) or a pass that moves to the next layer. **Never emit
ROOT_CAUSE_FOUND without a failing probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior API Gateway engineer knows from
incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **Lambda proxy response MUST include `statusCode` as an integer.** A
  REST API Lambda proxy function returning `{status: 200, body: "ok"}`
  (note: `status`, not `statusCode`) produces
  `Execution failed due to configuration: Malformed Lambda proxy response`.
  The same applies to a string statusCode (`"200"`) in some runtimes.
  Operators debug this as a Lambda failure because the function executed
  successfully — the response contract is the issue, not the code.

- **A function that throws an unhandled exception produces a 502, not a
  500.** If the Lambda function rejects (Promise reject, uncaught throw,
  `Runtime.LogError`), API Gateway receives no valid proxy response and
  returns 502. The error is in Lambda logs, not API Gateway. A common
  trap: the function works locally but fails in production due to a
  missing env var or IAM permission — the error surfaces as 502 in API
  Gateway, masking the real cause.

- **`Task timed out` in Lambda logs produces a 504, not 502.** When
  Lambda kills the function at its configured timeout, API Gateway
  receives no response and returns 504. The signature is
  `Task timed out after X.00 seconds` in the Lambda log, with the
  matching 504 timestamp in API Gateway access logs. Do NOT confuse
  this with a Lambda runtime error (which produces 502).

- **The 29-second integration timeout is a hard ceiling for REST APIs.**
  Even if Lambda is configured with `Timeout: 900` (15 minutes), API
  Gateway returns 504 at 29 seconds for REST APIs (30 seconds for HTTP
  APIs). The Lambda function continues running to completion — the client
  sees 504 while Lambda logs show success. Always compare
  `aws lambda get-function-configuration Timeout` against the 29s ceiling.
  If Lambda Timeout > 29, BACKEND_TIMEOUT_MISMATCH is the cause.

- **HTTP API (v2) `SimpleProxy` integrations have a slightly different
  error string.** The same malformed Lambda proxy response on an HTTP API
  produces `[InvalidResponseContent] ...` or a 502 without the
  "Malformed Lambda proxy response" string. Do NOT pattern-match on the
  REST API error string when diagnosing an HTTP API.

- **Stage-level throttling applies BEFORE the integration is invoked.**
  When the stage rate limit or burst limit is exceeded, API Gateway
  returns 503 without ever calling the Lambda function. Lambda
  ConcurrentExecutions will NOT spike — the request was rejected upstream.
  The signature is 5xxError spiking while Lambda Invocations does NOT
  spike. This distinguishes THROTTLE_STAGE from BACKEND_LAMBDA_ERROR.

- **Account-level Lambda concurrency limit produces 502, not 503, on some
  configurations.** When Lambda concurrent executions hit the account
  reserved limit, Lambda returns `TooManyRequestsException` (HTTP 429).
  API Gateway maps this to 502 for REST API Lambda proxy integrations —
  NOT 503. The signature is Lambda Throttles metric spiking alongside
  API Gateway 5xxError. Check Lambda throttling, not just API Gateway
  throttling.

- **Usage plan throttling only applies to API-key-authenticated requests.**
  A request without an API key (or with an invalid key) bypasses the usage
  plan entirely and is subject only to stage-level throttling. A 503
  during traffic peaks with no usage-plan throttle breach likely means
  stage-level or concurrency throttling — check which layer applies to
  the failing requests.

- **VPC Link integrations do NOT have per-target health checks in API
  Gateway.** API Gateway delegates to the NLB. If the NLB target group
  has no healthy targets, API Gateway returns 502 (not 503). The
  signature is `502 BadGateway` with `integrationStatus: 502` and no
  Lambda invocation in CloudTrail. The fix is in the NLB target group,
  not API Gateway.

- **A deployment is required for integration changes to take effect.**
  Modifying a method, integration, or stage setting via `update-method`
  or `update-integration` does NOT change the live API until a new
  deployment is created (`create-deployment`). An operator who "fixed"
  the timeout but forgot to deploy leaves the OLD configuration live.
  Always verify `deploymentId` in `get-stage` matches the latest
  deployment timestamp.

- **HTTP integration (non-Lambda) 502s often come from SSL handshake
  failures.** If the backend uses HTTPS with a self-signed or expired
  certificate, API Gateway cannot establish the connection and returns
  502. The access log shows `integrationErrorMessage` referencing the SSL
  error. The fix is on the backend certificate, not the API Gateway
  integration.

- **Payload size limit is 10 MB for both REST and HTTP APIs.** A request
  body exceeding 10 MB receives a 413 from API Gateway — but if the
  integration is Lambda proxy and the function also has a payload limit
  (6 MB synchronous invocation), the failure can surface as 502. Check
  both the request size (access log `requestSize`) and the Lambda
  payload (InvocationError in CloudTrail).

- **Access logs must be enabled to diagnose intermittent 5xx.** Without
  access logs, you have only aggregate CloudWatch metrics — no per-request
  `integrationErrorMessage`, `responseLatency`, or `integrationStatus`.
  Operators who "see 5xx in CloudWatch but no detail" almost always have
  access logs disabled. Enable them as the first remediation step.

- **CloudWatch metrics dimension differs between REST and HTTP APIs.**
  REST API metrics use `ApiName` + `Stage`. HTTP API metrics use `ApiId`
  + `Stage`. Querying with the wrong dimension returns no data points —
  a common cause of "the metrics show nothing" during a live incident.

### Step 1: Symptom entry — pick the diagnostic branch

Map the 5xx error code to a branch and jump to that branch's section.

| Error code | Meaning | Branch |
|---|---|---|
| **502 BadGateway** | Backend returned an invalid response or failed to respond at all | Step 2 |
| **504 GatewayTimeout** | Backend did not respond within the integration timeout (29s REST / 30s HTTP) | Step 3 |
| **503 ServiceUnavailable** | API Gateway or Lambda throttled the request before reaching the backend | Step 4 |
| **500 InternalServerError** | API Gateway internal failure (rare) | Step 5 |
| Ambiguous / intermittent / mixed codes | Gather access logs first | Step 1b |

### Step 1b: Gather access logs (when the code is ambiguous)

If the operator reports "we're getting 5xx" without a specific code, or
the code varies request-to-request, enable or fetch access logs first.

**REST API access log format (recommended JSON):**
```json
{
  "requestId": "$context.requestId",
  "status": "$context.status",
  "integrationStatus": "$context.integrationStatus",
  "integrationErrorMessage": "$context.integrationErrorMessage",
  "responseLatency": "$context.responseLatency",
  "integrationLatency": "$context.integrationLatency",
  "httpMethod": "$context.httpMethod",
  "resourcePath": "$context.resourcePath",
  "sourceIp": "$context.identity.sourceIp"
}
```

```bash
# Fetch access logs from CloudWatch Logs
aws logs filter-log-events \
  --log-group-name /aws/apigateway/<api>/<stage> \
  --filter-pattern '"status":50' \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json | jq '.events[].message'
```

The `integrationErrorMessage` field is the single most valuable signal —
it pinpoints the exact failure (Malformed Lambda proxy response, Execution
failed due to a timeout error, etc.).

### Step 2: 502 BadGateway — backend returned invalid response

Symptom: client receives `502 BadGateway`. API Gateway reached the backend
(or tried to) but received no valid response. This is the most common 5xx
on API Gateway.

Probe order (determine integration type first, then probe the matching
layer):

#### 2a: Lambda integration — runtime error or crash

```bash
# Fetch the Lambda function's recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --filter-pattern '"ERROR"' \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json | jq '.events[].message'

# Also check for runtime-level errors (Task timed out, Runtime.LogError)
aws logs filter-log-events \
  --log-group-name /aws/lambda/<function-name> \
  --filter-pattern 'Task timed out' \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json | jq '.events[].message'

# CloudTrail — confirm the Lambda was invoked and check for errors
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=Invoke \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) \
  --end-time $(date -u +%FT%TZ) \
  --output json | \
  jq '.Events[] | select(.ResourceName == "<function-name>")'
```

**Verdict signals:**
- Lambda log shows `Runtime.LogError` or a stack trace at the matching
  timestamp → **ROOT_CAUSE_FOUND**, `LAYER: BACKEND_LAMBDA_ERROR`. The
  function crashed (unhandled exception, missing env var, IAM permission
  denied, null reference). The fix is in the Lambda code.
- Lambda log shows `Task timed out after X.00 seconds` → **ROOT_CAUSE_FOUND**,
  `LAYER: TIMEOUT_LAMBDA` (jump to Step 3a — the 502 is actually a timeout
  presentation).
- Lambda was NOT invoked (CloudTrail shows no Invoke events during the
  failure window) → the integration never reached Lambda. Move to Step 2b
  or check stage throttling (Step 4).

#### 2b: Lambda proxy — malformed response format

```bash
# Check the Lambda function's return shape by inspecting recent logs
# Lambda proxy logs the return value in some runtimes; otherwise test:
aws lambda invoke \
  --function-name <function-name> \
  --payload file://test-event.json \
  --log-type Tail \
  /tmp/response.json --query 'LogResult' --output text | base64 -d

# Inspect the response body
cat /tmp/response.json | jq .
```

**Verdict signals:**
- Response is a bare string, an Error object, or missing `statusCode` →
  **ROOT_CAUSE_FOUND**, `LAYER: BACKEND_RESPONSE_FORMAT`. The REST API
  Lambda proxy contract requires `{statusCode: <int>, body: <string>,
  headers: <object>}`. Common violations:
  - Returning `{status: 200}` instead of `{statusCode: 200}`.
  - Returning a raw string without wrapping in `{body: ...}`.
  - `body` is an object, not a JSON-stringified string.
  - `statusCode` is a string (`"200"`) instead of integer (`200`).
- Access log shows `integrationErrorMessage: Execution failed due to
  configuration: Malformed Lambda proxy response` → confirms
  BACKEND_RESPONSE_FORMAT without needing the Lambda invoke.

#### 2c: HTTP integration — backend invalid response

```bash
# Test the backend directly (bypassing API Gateway)
curl -v -X <method> https://<backend-host>/<path> -d '<test-payload>'

# Check the backend's health endpoint
curl -v https://<backend-host>/health

# If the backend is an ALB, check target health
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json
```

**Verdict signals:**
- Backend returns a non-HTTP response, closes the connection mid-stream,
  or returns an invalid status line → **ROOT_CAUSE_FOUND**,
  `LAYER: BACKEND_HTTP_INVALID`.
- SSL handshake fails (`curl: (35) error:14094410`) → the backend
  certificate is invalid/expired. **ROOT_CAUSE_FOUND**,
  `LAYER: BACKEND_HTTP_INVALID` (SSL).
- Backend is unreachable (connection refused/timeout) but the integration
  type is HTTP → the backend is down. **ROOT_CAUSE_FOUND**,
  `LAYER: BACKEND_HTTP_INVALID`.
- Access log shows `integrationErrorMessage` referencing SSL or connection
  error → confirms BACKEND_HTTP_INVALID.

#### 2d: VPC Link integration — NLB target unhealthy

```bash
# Identify the VPC Link and its associated NLB
aws apigateway get-integration --rest-api-id <id> --resource-id <rid> \
  --http-method <verb> --output json | \
  jq '.connectionId'  # This is the VPC Link ID (vpcl-xxx)

# Check the NLB target group health (find the NLB behind the VPC Link)
aws elbv2 describe-target-groups --load-balancer-arn <nlb-arn> --output json
aws elbv2 describe-target-health --target-group-arn <tg-arn> --output json

# Check the VPC Link itself
aws apigateway get-vpc-links --output json
```

**Verdict signals:**
- Target group has zero healthy targets (all `unhealthy` or `unused`) →
  **ROOT_CAUSE_FOUND**, `LAYER: BACKEND_VPC_LINK`. The NLB cannot route
  the request. Fix the target health (security group, application health,
  target port).
- VPC Link is in `FAILED` or `PENDING` state → **ROOT_CAUSE_FOUND**,
  `LAYER: BACKEND_VPC_LINK`.
- Targets are healthy but the target group port does not match the
  integration `connectionId` → misconfiguration. **ROOT_CAUSE_FOUND**,
  `LAYER: BACKEND_VPC_LINK`.

#### 2e: Mapping template error (non-proxy Lambda integration)

```bash
# Check the integration response mapping template
aws apigateway get-integration-response --rest-api-id <id> \
  --resource-id <rid> --http-method <verb> \
  --status-code 200 --output json | jq '.responseTemplates'

# Check CloudWatch Logs for mapping template evaluation errors
aws logs filter-log-events \
  --log-group-name /aws/apigateway/<api>/<stage> \
  --filter-pattern 'MappingTemplate' \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --output json
```

**Verdict signals:**
- Mapping template references a missing JSON path, or Velocity Template
  Language (VTL) syntax error → **ROOT_CAUSE_FOUND**,
  `LAYER: BACKEND_MAPPING_TEMPLATE`. The fix is in the integration
  response template, not the Lambda function.

### Step 3: 504 GatewayTimeout — backend did not respond in time

Symptom: client receives `504 GatewayTimeout`. API Gateway invoked the
backend but did not receive a response within the integration timeout.

#### 3a: Lambda function execution exceeded the integration timeout

```bash
# Lambda function configured timeout
aws lambda get-function-configuration --function-name <fn> --output json | \
  jq '.Timeout'

# Lambda Duration metric (actual execution time)
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<fn> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# API Gateway Latency metric (what the client experienced)
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name Latency \
  --dimensions Name=ApiName,Value=<api> Name=Stage,Value=<stage> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

**Verdict signals:**
- Lambda Duration Maximum > 29000ms (29s) while API Gateway reports 504 →
  **ROOT_CAUSE_FOUND**, `LAYER: TIMEOUT_LAMBDA`. The function is too slow.
  Fix: optimize the function (database query, downstream API call) or
  increase the integration timeout (if < 29s and Lambda timeout allows).
- Lambda log shows `Task timed out after X.00 seconds` where X ≤ 29 →
  **ROOT_CAUSE_FOUND**, `LAYER: TIMEOUT_LAMBDA`.

#### 3b: HTTP integration backend too slow

```bash
# Test the backend response time directly
time curl -X <method> https://<backend-host>/<path> -d '<test-payload>'

# If the backend is an ALB, check target_processing_time in access logs
# ALB access logs in S3:
aws s3 ls s3://<access-log-bucket>/<prefix>/ \
  --recursive | tail -20
```

**Verdict signals:**
- Backend takes > 29s (REST) or > 30s (HTTP API) to respond →
  **ROOT_CAUSE_FOUND**, `LAYER: TIMEOUT_HTTP`. The backend is too slow.
  Fix: optimize the backend, add caching, or use connection pooling.
- Backend ALB target_processing_time is high (> 25s) → the backend
  application is the bottleneck.

#### 3c: Timeout mismatch (Lambda timeout > integration timeout)

```bash
# Compare Lambda timeout to the integration timeout
LAMBDA_TIMEOUT=$(aws lambda get-function-configuration \
  --function-name <fn> --output json | jq '.Timeout')
echo "Lambda Timeout: ${LAMBDA_TIMEOUT}s"
echo "API Gateway integration timeout: 29s (REST) / 30s (HTTP API)"

# Check the integration timeout setting (if explicitly configured)
aws apigateway get-integration --rest-api-id <id> \
  --resource-id <rid> --http-method <verb> --output json | \
  jq '.timeoutInMillis'
```

**Verdict signals:**
- Lambda Timeout > 29 (REST) or > 30 (HTTP API) AND the function
  consistently runs > 29s → **ROOT_CAUSE_FOUND**,
  `LAYER: TIMEOUT_MISMATCH`. API Gateway returns 504 at the integration
  ceiling while Lambda continues executing (and billing). Fix: reduce
  Lambda Timeout to ≤ 29s (so the function fails fast and logs the
  error), OR optimize the function to complete within 29s.

### Step 4: 503 ServiceUnavailable — throttling

Symptom: client receives `503 ServiceUnavailable`. The request was
rejected before reaching the backend. There are three throttling layers.

#### 4a: Stage-level throttling (rate limit + burst limit)

```bash
# REST API stage throttling
aws apigateway get-stage --rest-api-id <id> --stage-name <stage> --output json | \
  jq '.methodSettings, .throttle'

# HTTP API stage throttling
aws apigatewayv2 get-stage --api-id <id> --stage-name <stage> --output json | \
  jq '.defaultRouteSettings'

# API Gateway Count metric (total requests)
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=<api> Name=Stage,Value=<stage> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 60 --statistics Sum --output json
```

**Verdict signals:**
- Stage `rateLimit` or `burstLimit` is set, and Count metric exceeds them
  during the failure window → **ROOT_CAUSE_FOUND**,
  `LAYER: THROTTLE_STAGE`. Fix: raise the stage throttle (if the backend
  can handle it), add a usage plan for per-key limiting, or add a queue.
- HTTP API `defaultRouteSettings.throttlingRateLimit` exceeded → same
  verdict.

#### 4b: Account-level Lambda concurrency limit

```bash
# Lambda account-level concurrency settings
aws lambda get-account-settings --output json | \
  jq '.AccountLimit'

# Lambda ConcurrentExecutions metric
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value=<fn> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum --output json

# Lambda Throttles metric (the smoking gun)
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=<fn> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

**Verdict signals:**
- Lambda Throttles metric > 0 during the failure window, AND
  ConcurrentExecutions hit the account limit (or function reserved
  limit) → **ROOT_CAUSE_FOUND**, `LAYER: THROTTLE_CONCURRENCY`.
  Note: this may surface as 502 (not 503) for Lambda proxy integrations
  because Lambda returns 429 TooManyRequests, which API Gateway maps to
  502. Check Lambda Throttles regardless of whether the client sees 502
  or 503.

#### 4c: Usage plan throttling (API-key-authenticated requests)

```bash
# Check usage plans associated with the API stage
aws apigateway get-usage-plans --output json | \
  jq '.items[] | select(.apiStages[]?.apiId == "<api-id>")'

# Check the usage for a specific API key in the failure window
aws apigateway get-usage --usage-plan-id <plan-id> \
  --key-id <key-id> \
  --start-date 2026-08-01 --end-date 2026-08-09 --output json
```

**Verdict signals:**
- Usage plan rate/burst/quota exceeded for the API key →
  **ROOT_CAUSE_FOUND**, `LAYER: THROTTLE_USAGE_PLAN`. Fix: raise the
  plan limits, or distribute requests across multiple keys.
- The failing requests did not include an API key → usage plan
  throttling does not apply. Move to Step 4a or 4b.

### Step 5: 500 InternalServerError — rare AWS-side failure

Symptom: client receives `500 InternalServerError`. This is rare and
usually indicates an AWS-side issue.

```bash
# Check AWS Health Dashboard for API Gateway events
aws health describe-events \
  --filter services=APIGATEWAY,eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json

# Check for a corrupted deployment (if 500 started after a deployment)
aws apigateway get-stage --rest-api-id <id> --stage-name <stage> --output json | \
  jq '.deploymentId'
aws apigateway get-deployment --rest-api-id <id> \
  --deployment-id <dep-id> --output json
```

**Verdict signals:**
- 500 sustained, no recent deployment, no throttling, clean backends →
  **ESCALATE**, `LAYER: INTERNAL_ERROR`. Surface the AWS Health event ARN
  and open a Support case.
- 500 started immediately after a deployment → potentially corrupted
  deployment. **ROOT_CAUSE_FOUND**, `LAYER: INTERNAL_ERROR`. Fix: create
  a new deployment (`aws apigateway create-deployment --rest-api-id <id>
  --stage-name <stage>`).
- 500 intermittent with no pattern → ESCALATE. This is outside customer
  control.

### Step 6: Escalate or NEED_MORE_INFO

If none of the above produced a positive root-cause match, OR the symptom
clearly indicates an AWS-side incident (region event, sustained 500),
emit one of:

- **ESCALATE** — AWS-side incident. Surface the AWS Health event ARN,
  the API id, the stage, and the relevant CloudTrail error. Recommend
  opening a Support case. Do NOT continue diagnosing; the cause is
  outside the customer's control.
- **NEED_MORE_INFO** — A specific probe requires operator input. List the
  missing pieces (access logs not enabled, CloudWatch metrics not
  available, ambiguous error code, missing Lambda log group access) and
  the next probe to run once the info is available.

## Output format

```text
TARGET: <api-id>/<stage> (integration: <type>)
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <BACKEND_LAMBDA_ERROR | BACKEND_RESPONSE_FORMAT | BACKEND_HTTP_INVALID |
        BACKEND_VPC_LINK | BACKEND_MAPPING_TEMPLATE | TIMEOUT_LAMBDA |
        TIMEOUT_HTTP | TIMEOUT_MISMATCH | THROTTLE_STAGE |
        THROTTLE_CONCURRENCY | THROTTLE_USAGE_PLAN | PAYLOAD_TOO_LARGE |
        INTERNAL_ERROR | UNKNOWN>
EVIDENCE:
  - <observed symptom — error code, error string, latency pattern>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <api-id>/<stage>. Proceed?
  (yes/no)"
```

### Worked example — 502 from malformed Lambda proxy response

```text
TARGET: abc123/prod (integration: AWS_PROXY Lambda)
VERDICT: ROOT_CAUSE_FOUND
REASON: The Lambda function returns a bare JSON object without the required
  statusCode field, producing "Malformed Lambda proxy response" in the API
  Gateway access log (Step 2b).
LAYER: BACKEND_RESPONSE_FORMAT
EVIDENCE:
  - Symptom: clients receive 502 BadGateway on POST /orders. API Gateway
    access log shows integrationErrorMessage: "Execution failed due to
    configuration: Malformed Lambda proxy response."
  - Probe: aws lambda invoke --function-name orders-handler ... returns
    {"order_id": 123} — missing statusCode, body, headers.
  - Passing: Lambda CloudWatch logs show no Runtime.LogError; Lambda
    Invocations metric confirms the function was called; CloudTrail shows
    no Throttles.
REMEDIATION:
  1. Update the Lambda function to return the proxy response format:
     {statusCode: 200, body: JSON.stringify({order_id: 123}),
      headers: {"Content-Type": "application/json"}}
  2. Deploy the API: aws apigateway create-deployment --rest-api-id abc123
     --stage-name prod
  3. Verify: POST /orders now returns 200.
CONFIRM: Before deploying, emit and await:
  "CONFIRM: About to create-deployment on abc123/prod. Proceed? (yes/no)"
```

### Worked example — 504 from timeout mismatch

```text
TARGET: def456/prod (integration: AWS_PROXY Lambda)
VERDICT: ROOT_CAUSE_FOUND
REASON: Lambda function timeout is configured at 60s but the REST API
  integration timeout is 29s — API Gateway returns 504 at 29s while the
  function continues running (Step 3c).
LAYER: TIMEOUT_MISMATCH
EVIDENCE:
  - Symptom: clients receive 504 GatewayTimeout on GET /reports after
    exactly 29 seconds.
  - Probe: aws lambda get-function-configuration returns Timeout: 60.
    The REST API integration timeout is 29s (hard ceiling).
  - Probe: Lambda Duration metric shows Maximum 45000ms — the function
    finishes at 45s, well after API Gateway returned 504 at 29s.
  - Passing: No Lambda Runtime.LogError; Lambda Throttles metric is zero;
    stage throttling not exceeded.
REMEDIATION:
  1. Reduce the Lambda Timeout to 29s so the function fails fast and
     logs the timeout error:
     aws lambda update-function-configuration --function-name reports-handler
       --timeout 29 --profile <p>
  2. Optimize the function to complete within 29s (database query tuning,
     caching, async processing for long-running reports).
  3. Alternatively, migrate to an async pattern: API Gateway returns 202
     immediately; the client polls or receives a webhook when the report
     is ready.
  4. Verify: GET /reports completes within 29s, or returns 202 for async.
```

### Worked example — 503 from stage-level throttling

```text
TARGET: ghi789/prod (integration: AWS_PROXY Lambda)
VERDICT: ROOT_CAUSE_FOUND
REASON: Stage prod has a rate limit of 100 rps and burst of 200; traffic
  peaked at 500 rps during the marketing campaign launch. API Gateway
  returned 503 for requests exceeding the throttle (Step 4a).
LAYER: THROTTLE_STAGE
EVIDENCE:
  - Symptom: clients receive 503 ServiceUnavailable during the 14:00 UTC
    traffic peak. No 502 or 504 reported.
  - Probe: aws apigateway get-stage returns methodSettings with
    throttlingRateLimit: 100, throttlingBurstLimit: 200.
  - Probe: CloudWatch Count metric for the stage shows Sum 300000 in the
    14:00-14:05 window (1000 rps average) — well above the 100 rps limit.
  - Passing: Lambda Throttles metric is zero (the function was not the
    bottleneck); Lambda ConcurrentExecutions is below the account limit;
    no usage plan is associated with the stage.
REMEDIATION:
  1. Raise the stage throttle to match expected peak traffic:
     aws apigateway update-stage --rest-api-id ghi789 --stage-name prod
       --patch-operations
       op=replace,path=/methods/*/throttling/rateLimit,value=1000,
       op=replace,path=/methods/*/throttling/burstLimit,value=2000
  2. Create a usage plan for per-API-key throttling to prevent a single
     client from exhausting the stage budget.
  3. Verify: CloudWatch 5xxError drops to zero after the throttle change.
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_FOUND without a failing probe that matches the
  symptom. "Must be the Lambda" without checking the Lambda logs or
  invoking the function directly erodes operator trust.

- NEVER confuse 502 and 504. A 502 means the backend responded invalidly
  (Lambda proxy format error, runtime crash, HTTP backend malformed
  response). A 504 means the backend did not respond in time (Lambda
  slow, HTTP backend slow, timeout mismatch). Probing Lambda logs for a
  504 that is actually an HTTP integration timeout wastes the incident
  window.

- NEVER treat `Task timed out after X seconds` in Lambda logs as a 502.
  When Lambda kills the function at its timeout, API Gateway returns 504
  (not 502). The Lambda log error string is the same for both — the API
  Gateway error code disambiguates.

- NEVER assume the Lambda function was invoked. Stage-level throttling
  rejects requests BEFORE invoking Lambda. Always check CloudTrail
  Invoke events or the Lambda Invocations metric — if there are no
  invocations during the failure window, the cause is upstream of Lambda.

- NEVER assume account-level Lambda concurrency throttling produces 503.
  Lambda returns 429 TooManyRequests when concurrency is exhausted; API
  Gateway maps this to 502 for REST API Lambda proxy integrations (not
  503). Always check the Lambda Throttles metric regardless of whether
  the client sees 502 or 503.

- NEVER forget that the 29-second integration timeout is a hard ceiling.
  A Lambda function with Timeout: 900 (15 min) behind a REST API will
  ALWAYS 504 at 29s. The Lambda console shows the function succeeding;
  the client sees 504. Always compare Lambda Timeout to the 29s ceiling.

- NEVER pattern-match on the REST API error string for HTTP APIs (v2).
  HTTP APIs produce a different error string for the same Lambda proxy
  format error (`[InvalidResponseContent]` instead of `Malformed Lambda
  proxy response`). Identify the API type first.

- NEVER assume a deployment happened. Integration, method, and stage
  changes require `create-deployment` to take effect. An operator who
  "fixed the timeout" but did not deploy leaves the OLD configuration
  live. Always verify `deploymentId` in `get-stage`.

- NEVER enable access logs and then expect historical data. Access logs
  only capture requests from the moment they are enabled forward. If
  access logs were disabled during the incident, you have only aggregate
  CloudWatch metrics — note this gap and recommend enabling access logs
  for future incidents.

- NEVER treat usage-plan throttling as the cause for requests without an
  API key. Usage plans only apply to API-key-authenticated requests. If
  the failing requests do not include an API key, usage-plan throttling
  is not the cause — check stage-level or concurrency throttling.

- NEVER conflate VPC Link health with Lambda health. VPC Link integrations
  delegate to the NLB; if the NLB target group has no healthy targets,
  API Gateway returns 502 (not 503). The Lambda function is not involved.
  Always check `describe-target-health` for VPC Link integrations.

- NEVER recommend increasing the integration timeout beyond 29s for REST
  APIs. It is a hard ceiling. The fix is function optimization, async
  patterns, or migration to HTTP API (30s) — not a longer timeout.

- NEVER assume the 10 MB payload limit is the cause without checking the
  access log `requestSize`. A 413 response from API Gateway is clear; a
  502 from Lambda proxy with a 6 MB+ payload is ambiguous. Check both.

- NEVER reset the Lambda function configuration without confirming the
  root cause. Redeploying or updating the function when the cause is
  stage throttling or VPC Link health does not fix the issue and
  obscures the diagnostic trail.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-deployment`, `update-stage`, `update-function-configuration`,
  `put-method`, `update-integration`), emit and await operator approval.
  Do NOT execute the CLI until the operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is read-only
  (`get-*`, `filter-log-events`, `get-metric-statistics`,
  `lookup-events`, `lambda invoke` with a test payload). Do not perform
  state-changing operations as diagnostic probes.

- **Deployment is required after config changes.** Modifying a method,
  integration, or stage setting does NOT change the live API until
  `create-deployment`. Always include the deployment step in
  remediation.

- **Lambda timeout reduction can cause failures.** Reducing Lambda
  Timeout from 60s to 29s to fix a timeout mismatch will cause the
  function to fail (with `Task timed out`) if it consistently runs > 29s.
  This is the desired behaviour (fail fast, log the error) but the
  operator must be warned.

- **Stage throttle changes apply immediately.** Raising the rate limit
  or burst limit takes effect without a deployment. But it exposes the
  backend to higher traffic — verify the backend can handle the new
  limits before raising them.

- **Access log enablement is non-disruptive** but requires a CloudWatch
  Logs destination (or S3). Verify the log group exists or create it
  before enabling access logs on the stage.

## Remediation guidance

### For BACKEND_RESPONSE_FORMAT — Lambda proxy malformed response

1. Update the Lambda function to return the proxy response format:
   ```javascript
   // Node.js — correct format
   return {
     statusCode: 200,                    // integer, not string
     body: JSON.stringify(result),       // body MUST be a string
     headers: { "Content-Type": "application/json" }
   };
   ```
   ```python
   # Python — correct format
   return {
       "statusCode": 200,
       "body": json.dumps(result),
       "headers": {"Content-Type": "application/json"}
   }
   ```
2. Deploy the Lambda function (`aws lambda update-function-code`).
3. Deploy the API: `aws apigateway create-deployment --rest-api-id <id>
   --stage-name <stage>`.
4. Verify: the endpoint returns 200 with the expected body.

### For BACKEND_LAMBDA_ERROR — Lambda runtime crash

1. Identify the exception in the Lambda CloudWatch Logs.
2. Fix the code (add null checks, env var validation, IAM permissions).
3. Redeploy the function and verify with a test invoke.

### For BACKEND_HTTP_INVALID — HTTP backend invalid response

1. Test the backend directly with `curl -v`.
2. If SSL handshake fails: renew/replace the backend certificate.
3. If the backend returns malformed HTTP: fix the backend application.
4. If the backend is unreachable: check the backend instance/ALB health.

### For BACKEND_VPC_LINK — NLB target unhealthy

1. Fix the target health:
   ```bash
   aws elbv2 describe-target-health --target-group-arn <tg-arn>
   # Address the unhealthy reason (Target.FailedHealthChecks, Target.Timeout)
   ```
2. Verify the VPC Link is `AVAILABLE`:
   `aws apigateway get-vpc-links`.
3. Verify the integration `connectionId` matches the VPC Link ID.

### For TIMEOUT_LAMBDA — Lambda too slow

1. Optimize the function (database query tuning, caching, async I/O).
2. Increase the integration timeout (if < 29s for REST):
   `aws apigateway update-integration --rest-api-id <id> --resource-id <rid>
   --http-method <verb> --patch-operations
   op=replace,path=/timeoutInMillis,value=29000`.
3. If the function genuinely needs > 29s: migrate to an async pattern
   (API Gateway returns 202; client polls or receives a webhook).

### For TIMEOUT_MISMATCH — Lambda timeout > integration timeout

1. Reduce the Lambda Timeout to ≤ 29s:
   `aws lambda update-function-configuration --function-name <fn> --timeout 29`.
2. Optimize the function to complete within 29s.
3. For long-running workloads: use Step Functions or async invocation.

### For THROTTLE_STAGE — stage-level throttling

1. Raise the stage throttle (verify the backend can handle it):
   ```bash
   aws apigateway update-stage --rest-api-id <id> --stage-name <stage> \
     --patch-operations \
     op=replace,path=/methods/*/throttling/rateLimit,value=1000,\
     op=replace,path=/methods/*/throttling/burstLimit,value=2000
   ```
2. Add a usage plan for per-key throttling.

### For THROTTLE_CONCURRENCY — Lambda concurrency limit

1. Request a concurrency quota increase via the Lambda console or:
   ```bash
   aws lambda put-function-concurrency --function-name <fn> \
     --reserved-concurrent-configurations ReservedConcurrentExecutions=500
   ```
2. Or add an SQS queue + Lambda consumer to smooth traffic spikes.

### For INTERNAL_ERROR — corrupted deployment

1. Create a new deployment:
   ```bash
   aws apigateway create-deployment --rest-api-id <id> --stage-name <stage>
   ```
2. If the 500 persists: escalate to AWS Support.

### For ESCALATE — AWS-side incident

1. Surface the AWS Health event ARN and API id.
2. Open a Support case with the time window and request IDs from access logs.

## Domain

AWS CloudOps / API Gateway Integration Diagnostics, Lambda Proxy Contract,
Throttling Analysis, and Incident Diagnosis.

## Recent AWS features (2024-2026)

- **HTTP API improvements (2024-2025):** HTTP APIs now support private
  integrations via VPC Lattice, expanding the integration surface beyond
  Lambda and HTTP backends. Diagnosing 502s on a Lattice-backed HTTP API
  requires checking the Lattice service network, not just the NLB.
- **Lambda SnapStart (2024-2025):** SnapStart reduces cold-start latency
  for Java functions. A 504 that previously correlated with cold starts
  may disappear after enabling SnapStart. But SnapStart does not help
  with warm-function timeouts — do not conflate the two.
- **API Gateway access log enhancements (2024):** New `$context` fields
  including `integrationLatency` and `integrationStatus` provide finer-
  grained per-request diagnostics. Enable access logs with these fields
  for the richest 5xx diagnosis surface.
- **Lambda response streaming (2024-2025):** Function URL response
  streaming changes the timeout model — streamed responses can exceed
  29s because the first byte is sent before processing completes. This
  does NOT apply to API Gateway integrations (which remain 29s/30s).
- **Account-level Lambda concurrency improvements (2025):** Per-function
  reserved concurrency and provisioned concurrency controls are more
  granular. Use provisioned concurrency to eliminate cold-start 502s on
  latency-sensitive APIs.

## AWS documentation

- **API Gateway Developer Guide** — https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html
- **API Gateway error codes** — https://docs.aws.amazon.com/apigateway/latest/api-gateway-known-issues.html
- **Set up Lambda proxy integrations** — https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
- **CloudWatch metrics for API Gateway** — https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-metrics-and-dimensions.html
- **API Gateway access logs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html
- **Lambda troubleshooting** — https://docs.aws.amazon.com/lambda/latest/dg/troubleshooting.html
- **AWS CLI API Gateway reference (v1)** — https://docs.aws.amazon.com/cli/latest/reference/apigateway/
- **AWS CLI API Gateway reference (v2)** — https://docs.aws.amazon.com/cli/latest/reference/apigatewayv2/
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
