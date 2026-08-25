---
name: apigateway-5xx-troubleshooter
description: Diagnoses Amazon API Gateway 5xx errors (500 InternalServerError, 502 BadGateway, 503 ServiceUnavailable, 504 Timeout) through a systematic diagnostic tree covering Lambda proxy response format errors, Lambda runtime crashes, HTTP backend invalid responses, VPC Link target health, throttling at stage/concurrency/usage-plan layers, integration timeout mismatches, and rare internal failures. Walks symptoms to root cause with CloudWatch metrics (5xxError, Latency), access logs (integrationErrorMessage, responseLatency), CloudTrail Invoke API calls, and Lambda LogError scans. Emits ROOT_CAUSE_FOUND with the specific failure layer or ESCALATE for AWS-side incidents. Use when API Gateway returns 5xx errors, Lambda proxy format errors, integration timeouts, or throttled requests.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error strings and stage/integration metadata. Live-account diagnosis uses aws apigateway get-stage, get-resources, get-method, get-integration, aws apigatewayv2 get-stage, aws lambda get-function-configuration, aws logs filter-log-events (Lambda LogError scan), aws cloudwatch get-metric-statistics, and aws cloudtrail lookup-events (AWS CLI v2, SSO or key-based...
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
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing an API Gateway 5xx error (500, 502, 503, 504), walking a symptom to the failed integration layer with verify and fix commands, validating a Lambda proxy response format, diagnosing integration timeouts, identifying stage/usage-plan/concurrency throttling, or triaging a "the API is returning 5xx" page where the root cause may be Lambda, the HTTP backend, VPC Link health, throttling, or timeout configuration — not necessarily API Gateway itself.
  when_not_to_use: Configuration posture audits (use apigateway-resource-policy-auditor), authoring resource policies, deploying new APIs (use the deploy task type), Lambda function code debugging beyond the integration contract, or 4xx error diagnosis (4xx is a client/auth problem, not a 5xx backend problem).
  activation_triggers: API Gateway 5xx error, API Gateway 502 BadGateway, API Gateway 504 timeout, API Gateway 503 throttled, API Gateway 500 InternalServerError, Lambda proxy malformed response, integration timed out, Execution failed due to a timeout error, Type Error in Lambda, Runtime.LogError, stage throttling exceeded, Lambda concurrent executions exceeded, API Gateway access logs 5xx, troubleshoot API Gateway
  invocation_schema: 'Input: either (a) a symptom description (error code 500/502/503/504, observed latency pattern, recent deployment), optionally paired with the API/stage metadata (get-rest-apis/get-stage output, integration type, Lambda function configuration), OR (b) a REST API id + stage name for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and LAYER ∈ {BACKEND_LAMBDA_ERROR, BACKEND_RESPONSE_FORMAT, BACKEND_HTTP_INVALID, BACKEND_VPC_LINK, BACKEND_MAPPING_TEMPLATE, TIMEOUT_LAMBDA, TIMEOUT_HTTP, TIMEOUT_MISMATCH, THROTTLE_STAGE, THROTTLE_CONCURRENCY, THROTTLE_USAGE_PLAN, PAYLOAD_TOO_LARGE, INTERNAL_ERROR, UNKNOWN}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: API Gateway, 5xx, 500, 502, 503, 504, BadGateway, ServiceUnavailable, GatewayTimeout, InternalServerError, Lambda proxy, integration timeout, throttling, rate limit, burst limit, concurrency, usage plan, VPC Link, mapping template, CloudWatch metrics, access logs, CloudTrail, troubleshooting
  tags: apigateway, app-integration, troubleshooting, 5xx, lambda, throttle, timeout, cloudwatch
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

Messenger-not-cause framing and the backend-layers litany:
[references/advanced-patterns.md](references/advanced-patterns.md).

## Philosophy

Senior-engineer philosophy (5xx code locality; Lambda proxy contract;
29s ceiling; three throttling layers): [references/advanced-patterns.md](references/advanced-patterns.md).

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

The seven read-only probes (stage config REST/HTTP, integration, Lambda
config, 5XXError metrics, AWS Health): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Full catalog (statusCode int, throw=502, Task timed out=504, 29s ceiling,
HTTP API strings, throttle layers, VPC Link, SSL, 10MB, dimensions): [references/advanced-patterns.md](references/advanced-patterns.md).

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

Access-log JSON format + filter-log-events fetch command:
[references/diagnostic-commands.md](references/diagnostic-commands.md).

### Step 2: 502 BadGateway — backend returned invalid response

Symptom: client receives `502 BadGateway`. API Gateway reached the backend
(or tried to) but received no valid response. This is the most common 5xx
on API Gateway.

Probe order (determine integration type first, then probe the matching
layer):

#### 2a: Lambda integration — runtime error or crash

Probe commands (Lambda log ERROR scan, Task timed out scan, CloudTrail
Invoke): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probe commands (lambda invoke with Tail, inspect response shape):
[references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probe commands (direct curl, health check, ALB target health):
[references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probe commands (integration connectionId, target groups + health,
get-vpc-links): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probe commands (get-integration-response templates, MappingTemplate log
scan): [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict signals:**
- Mapping template references a missing JSON path, or Velocity Template
  Language (VTL) syntax error → **ROOT_CAUSE_FOUND**,
  `LAYER: BACKEND_MAPPING_TEMPLATE`. The fix is in the integration
  response template, not the Lambda function.

### Step 3: 504 GatewayTimeout — backend did not respond in time

Symptom: client receives `504 GatewayTimeout`. API Gateway invoked the
backend but did not receive a response within the integration timeout.

#### 3a: Lambda function execution exceeded the integration timeout

Probe commands (Lambda Timeout config, Duration metric, API Gateway
Latency metric): [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict signals:**
- Lambda Duration Maximum > 29000ms (29s) while API Gateway reports 504 →
  **ROOT_CAUSE_FOUND**, `LAYER: TIMEOUT_LAMBDA`. The function is too slow.
  Fix: optimize the function (database query, downstream API call) or
  increase the integration timeout (if < 29s and Lambda timeout allows).
- Lambda log shows `Task timed out after X.00 seconds` where X ≤ 29 →
  **ROOT_CAUSE_FOUND**, `LAYER: TIMEOUT_LAMBDA`.

#### 3b: HTTP integration backend too slow

Probe commands (timed curl, ALB access logs in S3):
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict signals:**
- Backend takes > 29s (REST) or > 30s (HTTP API) to respond →
  **ROOT_CAUSE_FOUND**, `LAYER: TIMEOUT_HTTP`. The backend is too slow.
  Fix: optimize the backend, add caching, or use connection pooling.
- Backend ALB target_processing_time is high (> 25s) → the backend
  application is the bottleneck.

#### 3c: Timeout mismatch (Lambda timeout > integration timeout)

Probe commands (compare Lambda Timeout to the 29s/30s ceiling,
timeoutInMillis): [references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Probe commands (stage throttling REST + HTTP API, Count metric):
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict signals:**
- Stage `rateLimit` or `burstLimit` is set, and Count metric exceeds them
  during the failure window → **ROOT_CAUSE_FOUND**,
  `LAYER: THROTTLE_STAGE`. Fix: raise the stage throttle (if the backend
  can handle it), add a usage plan for per-key limiting, or add a queue.
- HTTP API `defaultRouteSettings.throttlingRateLimit` exceeded → same
  verdict.

#### 4b: Account-level Lambda concurrency limit

Probe commands (account concurrency settings, ConcurrentExecutions,
Throttles metrics): [references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict signals:**
- Lambda Throttles metric > 0 during the failure window, AND
  ConcurrentExecutions hit the account limit (or function reserved
  limit) → **ROOT_CAUSE_FOUND**, `LAYER: THROTTLE_CONCURRENCY`.
  Note: this may surface as 502 (not 503) for Lambda proxy integrations
  because Lambda returns 429 TooManyRequests, which API Gateway maps to
  502. Check Lambda Throttles regardless of whether the client sees 502
  or 503.

#### 4c: Usage plan throttling (API-key-authenticated requests)

Probe commands (usage plans by apiId, get-usage per key window):
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Verdict signals:**
- Usage plan rate/burst/quota exceeded for the API key →
  **ROOT_CAUSE_FOUND**, `LAYER: THROTTLE_USAGE_PLAN`. Fix: raise the
  plan limits, or distribute requests across multiple keys.
- The failing requests did not include an API key → usage plan
  throttling does not apply. Move to Step 4a or 4b.

### Step 5: 500 InternalServerError — rare AWS-side failure

Symptom: client receives `500 InternalServerError`. This is rare and
usually indicates an AWS-side issue.

Probe commands (AWS Health events, deployment inspection):
[references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Further worked examples (504 timeout mismatch; 503 stage-level
throttling): [references/worked-examples.md](references/worked-examples.md).


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

All checks (confirmation gate, read-only-first, deploy-after-config,
timeout-reduction warning, throttle exposure, access-log enablement): [references/advanced-patterns.md](references/advanced-patterns.md).

## Remediation guidance

Per-LAYER remediation steps and fix commands (BACKEND_*, TIMEOUT_*,
THROTTLE_*, INTERNAL_ERROR, ESCALATE): [references/error-handling.md](references/error-handling.md).

## References (load on demand)

- [Worked examples](references/worked-examples.md) - full walkthroughs: 504 from timeout mismatch, 503 from stage-level throttling
- [Error handling](references/error-handling.md) - per-LAYER remediation steps and fix commands (BACKEND_*, TIMEOUT_*, THROTTLE_*, INTERNAL_ERROR, ESCALATE)
- [Diagnostic commands](references/diagnostic-commands.md) - the seven read-only pre-flight probes + every per-layer probe command block (Steps 1b, 2a-2e, 3a-3c, 4a-4c, 5)
- [Advanced patterns](references/advanced-patterns.md) - mindset, philosophy, Step 0 non-obvious behaviours, pre-flight safety checks, recent AWS features
- [Error codes and metrics](references/error-codes-and-metrics.md) - exact error strings, CloudWatch metric dimensions, access-log $context variables

## Domain

AWS CloudOps / API Gateway Integration Diagnostics, Lambda Proxy Contract,
Throttling Analysis, and Incident Diagnosis.

## Recent AWS features (2024-2026)

Recent AWS features (VPC Lattice, SnapStart, access-log $context fields,
response streaming, concurrency controls): [references/advanced-patterns.md](references/advanced-patterns.md).

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
