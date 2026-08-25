# Advanced patterns - API Gateway 5xx Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

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

## Step 0: non-obvious behaviours that change diagnosis

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

## Pre-flight safety checks

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
