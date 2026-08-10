---
description: Diagnose API Gateway 5xx errors (500, 502, 503, 504) through an error-code-driven diagnostic tree — identifies Lambda proxy format errors, integration timeouts, throttling, VPC Link issues, and emits ROOT_CAUSE_FOUND with the specific failure layer.
nl_triggers:
  - "API Gateway 5xx error"
  - "API Gateway 502 BadGateway"
  - "API Gateway 504 timeout"
  - "API Gateway 503 throttled"
  - "API Gateway 500 InternalServerError"
  - "Lambda proxy malformed response"
  - "Malformed Lambda proxy response"
  - "integration timed out"
  - "Execution failed due to a timeout error"
  - "Runtime.LogError"
  - "stage throttling exceeded"
  - "Lambda concurrent executions exceeded"
  - "API Gateway access logs 5xx"
  - "troubleshoot API Gateway 5xx"
  - "API Gateway returning errors"
  - "Lambda proxy 502"
routes_to: apigateway-5xx-troubleshooter
---

# /aws:troubleshoot-apigateway-5xx

Activate the `apigateway-5xx-troubleshooter` skill and diagnose an API
Gateway 5xx error through the error-code-driven diagnostic tree.

## What it does

Reads a symptom description (5xx error code, observed latency, recent
deployment) plus the API/stage metadata, then walks the error-code-
specific diagnostic tree to a root cause with positive evidence:

1. **Pre-flight** — API type (REST vs HTTP), integration type (Lambda
   proxy, HTTP, VPC Link), stage throttling settings, deployment
   timestamp. Short-circuits on missing context (NEED_MORE_INFO).
2. **Symptom entry** — map the 5xx code to a branch:
   - **502** → Lambda runtime error, Lambda proxy format, HTTP backend
     invalid response, VPC Link unhealthy target, mapping template.
   - **504** → Lambda slow, HTTP backend slow, timeout mismatch
     (Lambda Timeout > 29s integration ceiling).
   - **503** → stage-level throttling, usage-plan throttling, account-
     level Lambda concurrency (mapped to 502).
   - **500** → internal error (rare); check AWS Health Dashboard.
3. **Layer-specific probes** — Lambda logs (`Runtime.LogError`,
   `Task timed out`), Lambda invoke (response format check), HTTP
   backend direct curl, VPC Link target health, CloudWatch metrics
   (5xxError, Latency, Count, Lambda Throttles), access logs
   (`integrationErrorMessage`), CloudTrail Invoke events.
4. **Verdict** — ROOT_CAUSE_FOUND (with failing probe that matches the
   symptom), NEED_MORE_INFO (a probe requires operator input), or
   ESCALATE (AWS-side incident; surface AWS Health event ARN).

Emits a deterministic diagnostic block per target:

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
```

## When to invoke

Paste a symptom description and ask any of:

- "API Gateway returning 502 BadGateway"
- "Malformed Lambda proxy response"
- "504 GatewayTimeout on my API"
- "API Gateway 503 during traffic spike"
- "Lambda proxy returns 502 intermittently"
- "integration timed out API Gateway"
- "troubleshoot API Gateway 5xx errors"

A bare API id + any 5xx code ("abc123 is returning 502", "prod stage
has 504s") also routes here via the orchestrator.

## Inputs

- Symptom description: 5xx error code (500/502/503/504), observed
  latency, intermittent vs persistent pattern, recent deployment or
  config change.
- API/stage metadata: REST vs HTTP API, integration type, Lambda
  function configuration (timeout, memory, runtime), stage throttling
  settings, access-log status.
- For live-account diagnosis: API id, stage name, time window of the
  failure. The skill uses `get-stage`, `get-resources`, `get-method`,
  `get-integration`, `get-function-configuration`, `filter-log-events`,
  `get-metric-statistics`, `lookup-events`.

## Outputs

- One diagnostic block per target API/stage.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: Lambda code fix, deployment creation, throttle
  adjustment, VPC Link target health fix, or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for API Gateway 5xx).
- `/aws:audit-apigateway-resource-policy` for configuration posture
  audits on the same API (authorization, usage plans, WAF).
- `/aws:troubleshoot-lambda-invocation` for Lambda-specific diagnosis
  beyond the integration contract (cold starts, memory pressure).
