# API Gateway 5xx Error Codes and Metrics Reference

Supplementary reference for the API Gateway 5xx Troubleshooter skill.
This is loaded on-demand when a diagnostic needs the exact error string
patterns, CloudWatch metric dimensions, or access-log $context variables
for a specific 5xx code.

## 5xx error code catalog

### 500 InternalServerError

| Attribute | Detail |
|---|---|
| Meaning | API Gateway itself failed to process the request. |
| Frequency | Rare. |
| Typical cause | AWS-side incident; corrupted stage/deployment. |
| Action | Retry; if sustained, check AWS Health Dashboard and redeploy. |
| CloudWatch signal | 5XXError metric spikes with no corresponding Lambda error or throttle. |

### 502 BadGateway

| Attribute | Detail |
|---|---|
| Meaning | Backend returned an invalid response or no response at all. |
| Frequency | Most common API Gateway 5xx. |
| Typical causes | Lambda proxy format error; Lambda runtime crash; HTTP backend malformed response; VPC Link unhealthy target; Lambda concurrency throttle (mapped from 429). |
| Access log signal | `integrationErrorMessage` is non-empty. Common strings: `Malformed Lambda proxy response`, `[InvalidResponseContent]`, `Connection refused`, `SSL handshake failed`. |
| Action | Inspect Lambda logs for Runtime.LogError; inspect the response shape; test the backend directly. |

### 503 ServiceUnavailable

| Attribute | Detail |
|---|---|
| Meaning | API Gateway or Lambda throttled the request before it reached the backend. |
| Frequency | Common during traffic spikes. |
| Typical causes | Stage-level rate/burst exceeded; usage-plan rate/burst/quota exceeded; account-level Lambda concurrency exceeded (rare for 503 — usually 502). |
| Access log signal | `integrationStatus: -` (no integration invoked); `integrationLatency: 0`. |
| CloudWatch signal | Count spikes alongside 5xxError; Lambda Throttles metric may also spike. |
| Action | Raise stage/plan/concurrency limits; add a queue or usage plan. |

### 504 GatewayTimeout

| Attribute | Detail |
|---|---|
| Meaning | Backend did not respond within the integration timeout. |
| Frequency | Common for slow Lambda or slow HTTP backends. |
| Typical causes | Lambda Duration exceeds 29s (REST) or 30s (HTTP API); HTTP backend slow; Lambda Timeout configured > 29s (mismatch). |
| Access log signal | `integrationLatency` approaches 29000ms (REST) or 30000ms (HTTP API); `integrationErrorMessage: Execution failed due to a timeout error`. |
| CloudWatch signal | Latency metric spikes alongside 5xxError; Lambda Duration Maximum > 29000ms. |
| Action | Optimize the function/backend; reduce Lambda Timeout; migrate to async pattern. |

## Hard timeout ceilings

| API type | Integration timeout | Notes |
|---|---|---|
| REST API (v1) | **29,000 ms (29s)** | Hard ceiling. Cannot be raised. |
| HTTP API (v2) | **30,000 ms (30s)** | Hard ceiling. |
| Lambda function (max) | 900s (15 min) | Function can run longer than the integration timeout — but API Gateway will have already returned 504. |
| WebSocket API | 29s for `SEND` action; 2h for connection idle | Different model — not covered by this skill. |

## Lambda proxy response contract

### REST API (v1) — required fields

```json
{
  "statusCode": 200,
  "body": "{\"result\": \"ok\"}",
  "headers": {"Content-Type": "application/json"}
}
```

| Field | Type | Required | Common violations |
|---|---|---|---|
| `statusCode` | integer | YES | Returned as string `"200"`; missing entirely; returned as `status` (wrong key). |
| `body` | string | YES | Returned as a raw object (must be `JSON.stringify`-ed); missing. |
| `headers` | object | NO | If omitted, no custom headers are sent. If present, values must be strings. |
| `isBase64Encoded` | boolean | NO | Set to `true` if `body` is base64-encoded binary data. |

### HTTP API (v2) — same contract, different error string

The field requirements are identical to REST API. The error string on
malformed response differs:

| API type | Error string on malformed response |
|---|---|
| REST API (v1) | `Execution failed due to configuration: Malformed Lambda proxy response` |
| HTTP API (v2) | `[InvalidResponseContent] Invalid response body ...` or generic 502 |

## CloudWatch metrics for API Gateway

### Metrics namespace: `AWS/ApiGateway`

| Metric | Dimensions | What it tells you |
|---|---|---|
| `Count` | ApiName, Stage | Total requests. Spike during throttle-induced 503. |
| `4XXError` | ApiName, Stage | Client errors (auth, validation). Not relevant to 5xx diagnosis. |
| `5XXError` | ApiName, Stage | Backend/integration errors. The primary 5xx signal. |
| `Latency` | ApiName, Stage | Total time from request receipt to response sent. Includes integration time. Spike correlates with 504. |
| `IntegrationLatency` | ApiName, Stage | Time spent in the integration (Lambda/HTTP/VPC Link). Approaching 29000ms indicates timeout risk. |
| `CacheHitCount` | ApiName, Stage | Cache hits. Useful for diagnosing whether caching could relieve backend load. |

### HTTP API (v2) dimension difference

HTTP APIs use `ApiId` (not `ApiName`) as the dimension. A query with
`ApiName` returns no data points for an HTTP API.

```bash
# REST API metric query
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value=<api-name> Name=Stage,Value=<stage> ...

# HTTP API metric query (different dimension name)
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiId,Value=<api-id> Name=Stage,Value=<stage> ...
```

### Lambda metrics namespace: `AWS/Lambda`

| Metric | What it tells you for 5xx diagnosis |
|---|---|
| `Invocations` | Confirms the function was called. Zero during a 5xx window indicates upstream throttling. |
| `Errors` | Runtime errors and unhandled exceptions. Spike correlates with 502. |
| `Throttles` | Concurrency-limit throttling. Spike correlates with 502 (Lambda returns 429, mapped to 502). |
| `Duration` | Execution time. Maximum > 29000ms correlates with 504. |
| `ConcurrentExecutions` | Current concurrency. Approaching the account/function limit indicates throttle risk. |

## Access log $context variables

Enable access logs with these $context variables for the richest 5xx
diagnosis surface:

| Variable | What it captures |
|---|---|
| `$context.requestId` | Unique request ID — correlate with CloudTrail and Lambda logs. |
| `$context.status` | HTTP status returned to the client (the 5xx code). |
| `$context.integrationStatus` | Status from the integration. `-` means the integration was never invoked (throttling). |
| `$context.integrationErrorMessage` | The exact failure reason (e.g., `Malformed Lambda proxy response`). The single most valuable field. |
| `$context.responseLatency` | Total latency in ms. Approaching 29000ms indicates timeout. |
| `$context.integrationLatency` | Integration-only latency in ms. |
| `$context.httpMethod` | HTTP verb. Useful for correlating with a specific method. |
| `$context.resourcePath` | Resource path. Identifies the failing endpoint. |
| `$context.identity.sourceIp` | Client IP. Useful for rate-based attack diagnosis. |
| `$context.error.responseType` | Error type (e.g., `INTEGRATION_FAILURE`, `AUTHORIZATION_FAILURE`). |

### Recommended JSON log format

```
{"requestId":"$context.requestId","status":$context.status,"integrationStatus":"$context.integrationStatus","integrationErrorMessage":"$context.integrationErrorMessage","responseLatency":$context.responseLatency,"integrationLatency":$context.integrationLatency,"httpMethod":"$context.httpMethod","resourcePath":"$context.resourcePath","sourceIp":"$context.identity.sourceIp"}
```

## Integration error string quick lookup

| `integrationErrorMessage` (or access log error) | Layer | Step |
|---|---|---|
| `Execution failed due to configuration: Malformed Lambda proxy response` | BACKEND_RESPONSE_FORMAT | 2b |
| `[InvalidResponseContent]` (HTTP API v2) | BACKEND_RESPONSE_FORMAT | 2b |
| `Execution failed due to a timeout error` | TIMEOUT_LAMBDA / TIMEOUT_HTTP | 3 |
| `Connection refused` (HTTP integration) | BACKEND_HTTP_INVALID | 2c |
| `SSL handshake failed` / `error:14094410` | BACKEND_HTTP_INVALID (SSL) | 2c |
| `No integration response` | BACKEND_MAPPING_TEMPLATE | 2e |
| `TooManyRequestsException` (Lambda concurrency) | THROTTLE_CONCURRENCY | 4b |
| `Rate Exceeded` (stage throttle) | THROTTLE_STAGE | 4a |
| `500` with no integrationErrorMessage | INTERNAL_ERROR | 5 |

## VPC Link integration reference

### VPC Link to NLB mapping

```
Client → API Gateway → VPC Link (vpcl-xxx) → NLB → Target Group → Targets (EC2/IP)
```

| Component | Health check | Failure mode |
|---|---|---|
| VPC Link | `get-vpc-links` state | `FAILED` state → 502 |
| NLB | `describe-load-balancers` state | `failed` → 502 |
| Target Group | `describe-target-health` per target | All `unhealthy` → 502 |
| Target | Target health check (TCP/HTTP) | Application unhealthy → target `unhealthy` |

### Common VPC Link 502 causes

| Cause | Diagnostic |
|---|---|
| NLB target group has no healthy targets | `describe-target-health` returns all `unhealthy` or `unused` |
| Target SG does not allow NLB subnet CIDR on the target port | `describe-security-groups` on the target SG |
| Target group port mismatch | Compare `describe-target-groups Port` to the listener port |
| VPC Link in `PENDING` state | `get-vpc-links` — wait for `AVAILABLE` |
