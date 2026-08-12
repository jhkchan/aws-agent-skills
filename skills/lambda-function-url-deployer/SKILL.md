---
name: lambda-function-url-deployer
description: >-
  Provisions AWS Lambda Function URLs with production defaults: auth
  mode (AWS_IAM vs NONE), CORS configuration (allowOrigins,
  allowMethods, allowHeaders, exposeHeaders, maxAgeSeconds), invoke
  mode (BUFFERED vs RESPONSE_STREAM), 15-second timeout limit for
  function URL invocations, dual-stack IPv4/IPv6 endpoints, $LATEST
  alias constraint (cannot attach to a custom alias without
  UpdateFunctionUrl), CloudWatch metrics (UrlRequests, Url4xx,
  Url5xx, UrlLatency), cold start impact on first-byte latency,
  custom domain via CloudFront + Lambda URL, and pricing parity with
  standard Lambda invocations. Emits a READY_TO_DEPLOY checklist
  with verification commands. Use when creating a Lambda function
  URL, configuring CORS on a function URL, enabling response
  streaming, setting up IAM-authenticated function URLs, placing a
  custom domain in front of a function URL via CloudFront, or
  monitoring function URL metrics. Triggers: create lambda function
  url, configure cors on function url, enable response streaming
  lambda, lambda function url iam auth, lambda url cloudfront
  custom domain, lambda function url buffered vs response_stream.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with lambda
  access. Works with Terraform aws_lambda_function_url resource and
  CloudFormation AWS::Lambda::Url templates.
keywords:
  - aws
  - lambda
  - function url
  - cloudops
  - deploy
  - provisioning
  - cors
  - response streaming
  - iam auth
  - dual-stack
  - cloudfront
  - invoke mode
  - buffered
  - response_stream
tags:
  - aws
  - lambda
  - lambda-function-url
  - cloudops
  - deploy
  - compute
  - provisioning
  - cors
  - streaming
  - iam
  - cloudfront
  - dual-stack
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - lambda
    - lambda-function-url
    - cloudops
    - deploy
    - compute
    - provisioning
    - cors
    - streaming
    - iam
    - cloudfront
    - dual-stack
  dependencies:
    - aws-orchestrator
  keywords:
    - create lambda function url
    - configure cors on function url
    - enable response streaming lambda
    - lambda function url iam auth
    - lambda url cloudfront custom domain
    - lambda function url buffered vs response_stream
  when_to_use: >-
    Invoke when the user wants to create a Lambda Function URL,
    configure CORS on an existing function URL, switch invoke mode
    between BUFFERED and RESPONSE_STREAM, set up IAM-authenticated
    vs public (NONE auth) function URLs, place a custom domain
    (CloudFront) in front of a function URL, or monitor function URL
    CloudWatch metrics. Do NOT invoke for API Gateway HTTP/REST APIs
    (use apigateway skills), Lambda@Edge (use lambda-at-edge skills),
    or Application Load Balancer targets (use alb skills).
---

# Lambda Function URL Deployer

An AWS CloudOps agent skill that provisions AWS Lambda Function URLs
with correct defaults. The skill walks the auth-mode decision
(AWS_IAM vs NONE), CORS configuration at the function URL level,
invoke-mode decision (BUFFERED vs RESPONSE_STREAM), the 15-second
timeout limit for function URL invocations, dual-stack IPv4/IPv6
endpoints, the $LATEST alias constraint, CloudWatch metrics, cold
start impact, custom domain via CloudFront, and pricing parity,
captures configuration decisions, explains why each default matters,
and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create Lambda function URL, configure CORS on function URL, enable
response streaming Lambda, Lambda function URL IAM auth, Lambda URL
CloudFront custom domain, Lambda function URL BUFFERED vs
RESPONSE_STREAM, Lambda URL dual-stack.

## STRICT output contract

When this skill is invoked with a Lambda-function-URL-provisioning
request (create a function URL, configure CORS, switch invoke mode,
set up IAM auth, custom domain via CloudFront, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `LAMBDA_FUNCTION_URL:`, `VERDICT:`, `CHECKLIST:`,
and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist with
prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the
literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Function URL creation | Core creation step |
| Step 2 — Auth mode (AWS_IAM vs NONE) | Security decision |
| Step 3 — CORS configuration | Cross-origin access |
| Step 4 — Invoke mode (BUFFERED vs RESPONSE_STREAM) | Response behavior |
| Step 5 — Timeout limit (15 seconds) | Invocation timeout |
| Step 6 — Dual-stack IPv4/IPv6 | Network addressing |
| Step 7 — $LATEST alias constraint | Alias behavior |
| Step 8 — CloudWatch metrics | Observability |
| Step 9 — Cold start impact | Latency planning |
| Step 10 — Custom domain via CloudFront | Domain management |
| Step 11 — Pricing | Cost awareness |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/cors-and-auth.md | CORS + auth detail |
| references/streaming-and-cloudfront.md | Streaming + CloudFront detail |

## Mindset

**One-line takeaway:** A Lambda Function URL is a dedicated HTTP(S)
endpoint for your Lambda function. Auth is either AWS_IAM
(authenticated via SigV4) or NONE (public internet). CORS must be
configured at the function URL level, not on the Lambda function
itself. RESPONSE_STREAM mode enables streaming responses where the
first byte reaches the client faster than BUFFERED mode.

Four misconceptions dominate Lambda Function URL misdesign at
provisioning time:

- **"CORS is configured on the Lambda function."** It is not. CORS
  is configured at the Function URL level via the `--cors` parameter
  on `create-function-url-config` / `update-function-url-config`. A
  Lambda function has no CORS settings; the function URL does. A
  baseline model that configures CORS on the function itself (or in
  the handler response only) will leave the function URL's CORS
  policy empty, causing browser preflight failures.

- **"NONE auth is fine for everything."** NONE auth means the
  function URL is on the public internet with no authentication.
  Anyone who knows the URL can invoke it. For any authenticated
  workload, use AWS_IAM auth. The only valid NONE-auth use cases are
  public-facing endpoints (webhooks, public APIs) where you implement
  application-level auth inside the handler.

- **"BUFFERED and RESPONSE_STREAM are interchangeable."** They are
  not. BUFFERED mode waits for the entire response payload before
  returning (max 6 MB response, subject to the 15-second timeout).
  RESPONSE_STREAM mode streams the response body as it is generated
  (first byte faster, useful for LLM token streaming, progressive
  rendering, and long-running responses). RESPONSE_STREAM changes
  the handler signature (uses `responseStreamWriter`) and requires
  the runtime to support streaming (Node.js 14+, Python 3.9+ with
  wrapper).

- **"I can attach a function URL to any alias."** You cannot attach
  a function URL to a custom alias (e.g., `prod`, `staging`) without
  calling `update-function-url-config` with `--qualifier`. Function
  URLs are attached to the function or to `$LATEST` by default. To
  point a function URL at a specific alias, you must update the
  function URL config with the alias as the qualifier. A baseline
  model that creates an alias and assumes the URL follows it will
  produce a broken deployment.

## Configuration dependency graph (novel heuristic)

Lambda Function URL configurations are NOT independent. The function
must exist before the URL can be created. CORS is a property of the
URL config, not the function. The invoke mode determines the handler
signature. Auth mode cannot be changed without updating the URL
config. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Function URL creation | Lambda function exists; function is not a Lambda@Edge function | URL is created on the function or `$LATEST`; to point at a custom alias, must update with `--qualifier` | the HTTP endpoint |
| Auth mode (AWS_IAM) | Function URL exists | callers must sign requests with SigV4; missing SigV4 returns 403 | authenticated invocation |
| Auth mode (NONE) | Function URL exists | endpoint is public internet; no auth check; ALL internet traffic can invoke | public invocation |
| CORS configuration | Function URL exists | CORS is at the URL level, NOT the function; omitting CORS causes browser preflight failures | cross-origin browser access |
| Invoke mode (BUFFERED) | Function URL exists; handler returns a full payload | response capped at 6 MB; entire response buffered before return | standard request-response |
| Invoke mode (RESPONSE_STREAM) | Function URL exists; runtime supports streaming; handler uses `responseStreamWriter` | first byte faster; max response still bounded by 15s timeout for the function URL invocation | streaming response body |
| CloudFront distribution | Function URL exists (as origin) | CloudFront caches at edge; TTL must be tuned; no query-string forwarding by default | custom domain + TLS + edge caching |
| CloudWatch metrics | Function URL exists | metrics are automatic (no config needed); UrlRequests, Url4xx, Url5xx, UrlLatency | observability |

**The CORS-at-URL-level row is the one a baseline model misses.**
A baseline model configures CORS inside the Lambda handler's HTTP
response headers and assumes the browser will accept it. Without the
CORS policy on the function URL config itself, the browser preflight
(OPTIONS request) fails because the function URL does not return the
`Access-Control-Allow-*` headers for preflight. The procedure below
forces an explicit CORS decision.

**Cross-dependency gotchas:**
- Auth mode and CORS are independent but both live on the URL config.
  Changing auth mode does not change CORS and vice versa.
- RESPONSE_STREAM requires a handler signature change. Switching
  from BUFFERED to RESPONSE_STREAM without updating the handler
  produces a runtime error.
- CloudFront in front of a function URL with AWS_IAM auth requires
  a custom CloudFront Lambda@Edge or CloudFront Function to sign
  requests with SigV4. CloudFront cannot natively sign Lambda
  Function URL requests. For simpler setups, use NONE auth + a
  CloudFront WAF + application-level auth.
- The 15-second timeout is a hard limit for function URL invocations
  regardless of the function's configured timeout. If the function's
  timeout is 60 seconds, function URL invocations still time out at
  15 seconds.

## Expert heuristic: RESPONSE_STREAM first byte advantage

A baseline model says "use BUFFERED, it's simpler." The correct
heuristic recognizes that RESPONSE_STREAM reduces time-to-first-byte
dramatically for workloads where the response is generated
incrementally (LLM token streaming, progressive HTML rendering,
large data exports).

```text
BUFFERED mode timeline:
  Client → Function URL → Lambda handler runs fully → 200 OK + full payload
  Time to first byte = total handler execution time

RESPONSE_STREAM mode timeline:
  Client → Function URL → Lambda handler starts → 200 OK + first chunk
                             → next chunk
                             → next chunk
                             → final chunk + stream end
  Time to first byte = handler startup + first chunk generation time
```

**Key implication:** for LLM token streaming (streaming completions),
progressive rendering (streaming HTML), or any workload where the
client benefits from early data, RESPONSE_STREAM is the correct
choice. For simple request-response APIs where the full payload is
available quickly, BUFFERED is fine and simpler.

## Expert heuristic: CORS is at the function URL level

CORS for Lambda Function URLs is NOT set on the Lambda function or
in the handler alone. It is set on the function URL configuration
via the `--cors` parameter. This is a common provisioning mistake.

```text
WRONG (does not work alone):
  - Lambda handler returns Access-Control-Allow-Origin header
  - Function URL has NO CORS config
  → Browser preflight (OPTIONS) fails because the function URL
    does not return CORS headers for preflight

CORRECT:
  - Function URL config has --cors with allowOrigins, allowMethods,
    allowHeaders, exposeHeaders, maxAgeSeconds
  - Lambda handler ALSO returns Access-Control-Allow-Origin in the
    response (defense in depth)
  → Browser preflight succeeds (function URL handles OPTIONS with
    CORS headers); handler response includes CORS headers for the
    actual response
```

**Key implication:** always configure CORS at the function URL level
using the `--cors` parameter. The handler-level CORS header is a
secondary defense, not the primary CORS mechanism for function URLs.

## Expert heuristic: NONE auth is public internet

A baseline model may treat NONE auth as "no auth, like a public API
Gateway endpoint." The correct framing: NONE auth means the URL is
on the public internet with zero authentication. The only thing
stopping unauthorized invocations is the unguessability of the URL
endpoint ID (a 32-character string). This is NOT a security boundary.

```text
NONE auth invocation flow:
  Client → https://<id>.lambda-url.<region>.on.aws/ → Lambda handler
  No auth check. No IAM evaluation. No API key.
  Anyone with the URL can invoke.

AWS_IAM auth invocation flow:
  Client → signs request with SigV4 using IAM credentials
        → https://<id>.lambda-url.<region>.on.aws/ → Lambda handler
  IAM evaluates resource-based policy on the Lambda function.
  Unauthorized → 403 Forbidden.
```

**Key implication:** use NONE auth ONLY for genuinely public
endpoints (webhooks, public APIs with application-level auth). For
any internal or authenticated workload, use AWS_IAM auth with a
resource-based policy on the Lambda function.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Lambda function exists | Function URL requires an existing function | `aws lambda get-function --function-name <name>` |
| Function is NOT a Lambda@Edge function | Function URLs do not support Lambda@Edge | Verify the function is not published to CloudFront |
| Runtime supports streaming (if RESPONSE_STREAM) | RESPONSE_STREAM requires Node.js 14+, Python 3.9+ with wrapper, or Java 11+ | Check `aws lambda get-function-configuration --function-name <name> --query 'Runtime'` |
| IAM permissions for function URL management | Creating/updating function URLs requires `lambda:CreateFunctionUrlConfig`, `lambda:UpdateFunctionUrlConfig` | Verify IAM policy |
| CORS origins identified | CORS allowOrigins must be explicit for production | Confirm allowed origins |
| Auth-mode decision | AWS_IAM vs NONE is a security decision | Assess whether endpoint is public or authenticated |
| CloudFront distribution (if custom domain) | Custom domain requires CloudFront in front of the function URL | Verify CloudFront distribution exists |
| Resource-based policy (if AWS_IAM auth) | IAM auth evaluates the function's resource-based policy | Verify policy allows intended callers |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Function URL creation

A Lambda Function URL is created via
`create-function-url-config`. It attaches a dedicated HTTPS endpoint
to the function (or to `$LATEST` by default).

```bash
# Create a function URL with AWS_IAM auth and BUFFERED invoke mode
aws lambda create-function-url-config \
  --function-name my-function \
  --auth-type AWS_IAM \
  --invoke-mode BUFFERED \
  --cors '{
    "AllowOrigins": ["https://example.com"],
    "AllowMethods": ["GET", "POST"],
    "AllowHeaders": ["content-type", "authorization"],
    "ExposeHeaders": ["date", "x-request-id"],
    "MaxAgeSeconds": 86400
  }' \
  --region us-east-1
```

The response includes the `FunctionUrl` — the HTTPS endpoint:

```text
https://<id>.lambda-url.<region>.on.aws/
```

**Verify the function URL was created:**

```bash
aws lambda get-function-url-config \
  --function-name my-function \
  --region us-east-1
```

**Common mistake:** trying to create a function URL on a function
that does not exist yet. The function must be created first.

## Step 2 — Auth mode (AWS_IAM vs NONE)

| Feature | AWS_IAM | NONE |
|---|---|---|
| Authentication | SigV4 signed requests using IAM credentials | No auth (public internet) |
| Authorization | Resource-based policy on the Lambda function | None — anyone with the URL can invoke |
| Use case | Internal APIs, authenticated endpoints | Public webhooks, public APIs with app-level auth |
| Client complexity | Must sign requests (SDK does this automatically) | Simple HTTP call (curl, fetch) |
| Security boundary | IAM policy evaluation | None (URL unguessability is NOT security) |

**NONE auth is public internet.** The only protection is the
unguessability of the URL endpoint ID. Do NOT use NONE auth for
anything that should not be publicly accessible.

**AWS_IAM auth requires a resource-based policy** on the Lambda
function that grants `lambda:InvokeFunctionUrl` to the intended
callers:

```bash
# Add a resource-based policy allowing a principal to invoke the URL
aws lambda add-permission \
  --function-name my-function \
  --statement-id function-url-invoke \
  --action lambda:InvokeFunctionUrl \
  --principal arn:aws:iam::111122223333:user/alice \
  --function-url-auth-type AWS_IAM \
  --region us-east-1
```

For cross-account access, set `--principal` to the other account's
ARN. For service access (e.g., API Gateway, CloudFront), use the
service principal.

## Step 3 — CORS configuration

CORS is configured at the Function URL level, NOT on the Lambda
function. The `--cors` parameter accepts a JSON object with five
fields:

| Field | Description | Example |
|---|---|---|
| `AllowOrigins` | Origins permitted to make cross-origin requests | `["https://example.com", "https://app.example.com"]` |
| `AllowMethods` | HTTP methods permitted in cross-origin requests | `["GET", "POST", "OPTIONS"]` |
| `AllowHeaders` | Request headers permitted in cross-origin requests | `["content-type", "authorization"]` |
| `ExposeHeaders` | Response headers the browser can read | `["date", "x-request-id"]` |
| `MaxAgeSeconds` | How long (seconds) the browser caches preflight results | `86400` |

**Create a function URL with full CORS:**

```bash
aws lambda create-function-url-config \
  --function-name my-function \
  --auth-type AWS_IAM \
  --invoke-mode BUFFERED \
  --cors '{
    "AllowOrigins": ["https://example.com"],
    "AllowMethods": ["GET", "POST"],
    "AllowHeaders": ["content-type", "authorization"],
    "ExposeHeaders": ["date", "x-request-id"],
    "MaxAgeSeconds": 86400
  }' \
  --region us-east-1
```

**Update CORS on an existing function URL:**

```bash
aws lambda update-function-url-config \
  --function-name my-function \
  --cors '{
    "AllowOrigins": ["https://example.com", "https://staging.example.com"],
    "AllowMethods": ["GET", "POST", "PUT", "DELETE"],
    "AllowHeaders": ["content-type", "authorization", "x-api-key"],
    "ExposeHeaders": ["date", "x-request-id", "x-trace-id"],
    "MaxAgeSeconds": 3600
  }' \
  --region us-east-1
```

**Critical:** without CORS configuration at the function URL level,
browser-based clients will fail preflight (OPTIONS) requests. Server-
side clients (curl, SDKs) are not affected by CORS — CORS is a
browser-enforced policy.

## Step 4 — Invoke mode (BUFFERED vs RESPONSE_STREAM)

| Feature | BUFFERED | RESPONSE_STREAM |
|---|---|---|
| Response delivery | Entire payload buffered before return | Streamed as generated |
| Time to first byte | Total handler execution time | Handler startup + first chunk |
| Max response size | 6 MB | Effectively bounded by 15s timeout |
| Handler signature | Standard `return {statusCode, body}` | Uses `responseStreamWriter` |
| Runtime support | All runtimes | Node.js 14+, Python 3.9+ (wrapper), Java 11+ |
| Use case | Simple request-response | LLM token streaming, progressive rendering, large exports |

**BUFFERED handler (Node.js):**

```javascript
exports.handler = async (event) => {
  return {
    statusCode: 200,
    body: JSON.stringify({ message: "Hello" })
  };
};
```

**RESPONSE_STREAM handler (Node.js):**

```javascript
exports.handler = awslambda.streamifyResponse(
  async (event, responseStream, context) => {
    responseStream.setContentType("text/plain");
    responseStream.write("First chunk\n");
    // Simulate incremental work
    await new Promise(r => setTimeout(r, 100));
    responseStream.write("Second chunk\n");
    responseStream.end();
  }
);
```

**Create a function URL with RESPONSE_STREAM:**

```bash
aws lambda create-function-url-config \
  --function-name my-streaming-function \
  --auth-type NONE \
  --invoke-mode RESPONSE_STREAM \
  --cors '{"AllowOrigins":["*"],"AllowMethods":["GET","POST"]}' \
  --region us-east-1
```

**Critical:** switching invoke mode requires updating the handler
signature. A BUFFERED handler deployed on a RESPONSE_STREAM function
URL produces a runtime error. Test the handler with the correct
invoke mode before deploying.

## Step 5 — Timeout limit (15 seconds)

Function URL invocations are capped at **15 seconds** regardless of
the function's configured timeout. If the function's timeout is set
to 60 seconds, function URL invocations still time out at 15 seconds.

```text
Lambda function timeout: 60 seconds (configured on the function)
Function URL invocation timeout: 15 seconds (hard limit)
Direct invocation (SDK/CLI): respects the 60-second timeout
Function URL invocation: capped at 15 seconds → HTTP 504
```

**Implications:**
- Long-running workloads (> 15 seconds) cannot be served via
  function URLs synchronously. Use async invocation, Step Functions,
  or EventBridge for long-running processing.
- RESPONSE_STREAM mode can keep the connection alive by streaming
  data within the 15-second window. The first byte must arrive before
  the timeout; subsequent chunks stream until the 15-second limit.

**Verify the function's configured timeout:**

```bash
aws lambda get-function-configuration \
  --function-name my-function \
  --query 'Timeout' \
  --region us-east-1
```

If the timeout exceeds 15 seconds and the workload is served via
function URL, warn the operator that function URL invocations cap at
15 seconds.

## Step 6 — Dual-stack IPv4/IPv6

Lambda Function URLs are dual-stack — they resolve to both IPv4 and
IPv6 addresses. The URL format is:

```text
https://<id>.lambda-url.<region>.on.aws/
```

The endpoint supports both IPv4 and IPv6 connections. No additional
configuration is needed — dual-stack is automatic.

**Implications:**
- Clients on IPv6-only networks (rare but growing) can reach
  function URLs without NAT64 or other translation.
- Security groups and WAF rules must account for both IPv4 and IPv6
  source addresses if filtering by IP.
- CloudFront in front of a function URL connects via IPv4 by
  default. For IPv6 client support through CloudFront, enable IPv6
  on the CloudFront distribution.

## Step 7 — $LATEST alias constraint

Function URLs are attached to the function or to `$LATEST` by
default. To point a function URL at a specific alias (e.g., `prod`,
`staging`), you must update the function URL config with the alias
as the qualifier.

```bash
# Create function URL pointing at $LATEST (default)
aws lambda create-function-url-config \
  --function-name my-function \
  --auth-type AWS_IAM \
  --invoke-mode BUFFERED

# Update function URL to point at the 'prod' alias
aws lambda update-function-url-config \
  --function-name my-function \
  --qualifier prod \
  --auth-type AWS_IAM \
  --invoke-mode BUFFERED
```

**Common mistake:** creating an alias (e.g., `prod`) and assuming
the function URL automatically follows it. It does not. The
function URL must be explicitly updated with `--qualifier prod`.

**Verify the qualifier:**

```bash
aws lambda get-function-url-config \
  --function-name my-function \
  --qualifier prod \
  --region us-east-1
```

**Key implication:** when promoting code from staging to production
via alias shifting, update the function URL's qualifier if you want
the URL to point at the new alias.

## Step 8 — CloudWatch metrics

Lambda Function URLs emit the following CloudWatch metrics
automatically (no configuration needed):

| Metric | Description | Dimension |
|---|---|---|
| `UrlRequests` | Number of invocation requests received by the function URL | FunctionName |
| `Url4xx` | Number of requests that returned a 4xx error | FunctionName |
| `Url5xx` | Number of requests that returned a 5xx error | FunctionName |
| `UrlLatency` | Time from when the function URL receives the request to when it returns the response | FunctionName |

These metrics are in the `AWS/Lambda` namespace.

**Monitor function URL metrics via CLI:**

```bash
# Get UrlRequests for the last hour
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name UrlRequests \
  --dimensions Name=FunctionName,Value=my-function \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1

# Get Url5xx errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Url5xx \
  --dimensions Name=FunctionName,Value=my-function \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

**Set up alarms for 5xx errors:**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "lambda-url-5xx-my-function" \
  --metric-name Url5xx \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=my-function \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --period 300 \
  --evaluation-periods 1 \
  --statistic Sum \
  --region us-east-1
```

## Step 9 — Cold start impact

Cold starts affect function URL invocations the same way they affect
direct Lambda invocations. When a function has not been invoked
recently, the first invocation includes initialization time (loading
the runtime, loading the handler code, running the init code).

```text
Warm invocation latency:
  Client → Function URL → Lambda (warm) → Response
  Total = handler execution time

Cold invocation latency:
  Client → Function URL → Lambda (cold) → Init runtime → Init code → Handler → Response
  Total = init time + handler execution time
  Init time can be 100ms–several seconds depending on package size and runtime
```

**Mitigations:**
- Use Provisioned Concurrency to pre-initialize execution
  environments and eliminate cold starts. Function URLs support
  provisioned concurrency.
- Keep the deployment package small. Large packages increase init
  time.
- Use lighter runtimes (e.g., Node.js, Python) over heavier ones
  (e.g., Java) if cold start is critical.
- RESPONSE_STREAM mode reduces perceived cold start latency because
  the first byte is sent as soon as the handler starts, not after
  the full response is ready.

**Provisioned concurrency with function URL:**

```bash
# Set up provisioned concurrency on an alias
aws lambda put-provisioned-concurrency-config \
  --function-name my-function \
  --qualifier prod \
  --provisioned-concurrent-executions 10 \
  --region us-east-1
```

The function URL must point at the alias (`--qualifier prod`) to
benefit from provisioned concurrency.

## Step 10 — Custom domain via CloudFront + Lambda URL

Lambda Function URLs do not natively support custom domains. To use
a custom domain (e.g., `api.example.com`), place a CloudFront
distribution in front of the function URL.

```text
Client → CloudFront (custom domain: api.example.com)
       → Origin: https://<id>.lambda-url.<region>.on.aws/
       → Lambda function URL → Lambda handler
```

**CloudFront distribution for a function URL:**

```bash
# Create a CloudFront distribution with the function URL as origin
aws cloudfront create-distribution \
  --origin-domain-name "abc123def456.lambda-url.us-east-1.on.aws" \
  --default-cache-behavior '{
    "TargetOriginId": "lambda-url-origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "TrustedSigners": {"Enabled": false, "Quantity": 0},
    "ForwardedValues": {
      "QueryString": true,
      "Cookies": {"Forward": "none"},
      "Headers": {"Quantity": 0}
    },
    "MinTTL": 0,
    "DefaultTTL": 0,
    "MaxTTL": 0
  }' \
  --enabled \
  --region us-east-1
```

**Critical considerations for CloudFront + function URL:**
- Set `DefaultTTL=0` (no caching) unless the function returns
  cacheable content.
- Enable query string forwarding (`QueryString: true`) if the
  handler reads query parameters.
- For AWS_IAM auth function URLs, CloudFront cannot natively sign
  requests. Use NONE auth + CloudFront WAF + application-level auth,
  or use a Lambda@Edge / CloudFront Function to sign requests.
- For custom domain TLS, attach an ACM certificate to the CloudFront
  distribution.
- CloudFront adds latency (an extra hop) but provides edge caching,
  DDoS protection, and custom domain support.

**Attach a custom domain (ACM + CloudFront):**

```bash
# Request an ACM certificate (us-east-1 required for CloudFront)
aws acm request-certificate \
  --domain-name api.example.com \
  --validation-method DNS \
  --region us-east-1

# After validation, associate the certificate with CloudFront
# (done via CloudFront distribution update)
```

## Step 11 — Pricing

Lambda Function URLs are priced the same as standard Lambda
invocations. There is no additional charge for the function URL
itself.

| Cost component | Pricing |
|---|---|
| Requests | Same as standard Lambda invocation pricing |
| Compute duration | Same as standard Lambda (GB-seconds) |
| Data transfer OUT | Standard AWS data transfer rates |
| Function URL endpoint | No additional charge |

**Cost formula:**

```text
Monthly cost = (requests × $0.20/million)
             + (compute GB-seconds × $0.0000166667/GB-second)
             + data transfer OUT
```

**Implications:**
- Function URLs are cost-effective for HTTP endpoints. No API
  Gateway per-request pricing.
- For high-volume APIs with throttling, usage plans, or API keys,
  API Gateway may be more appropriate despite higher per-request
  cost, because function URLs do not support these features.
- RESPONSE_STREAM mode does not cost more than BUFFERED — the
  billing is based on invocation + duration, not on streaming.

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **RESPONSE_STREAM invoke mode (2023-2024):** Added support for
  streaming responses from function URLs. Enables LLM token
  streaming, progressive rendering, and long-running response
  scenarios. Requires a handler signature change and a runtime that
  supports streaming.

- **Function URL IAM auth enhancements (2023-2024):** Improved
  support for cross-account IAM access via resource-based policies.
  The `function-url-auth-type` parameter on `add-permission`
  enables fine-grained control over who can invoke the URL.

- **Provisioned concurrency for function URLs (2023-2024):**
  Function URLs now fully support provisioned concurrency when
  pointed at an alias with a provisioned concurrency configuration.
  This eliminates cold starts for latency-sensitive workloads.

- **CloudFront integration patterns (2024-2025):** Expanded
  guidance and patterns for placing CloudFront in front of function
  URLs, including origin access control patterns, WAF integration,
  and custom domain management.

- **Function URL metrics in CloudWatch (2024-2025):** Enhanced
  metric granularity for function URL invocations, including
  per-qualifier metrics and integration with CloudWatch
  dashboards and alarms.

## NEVER do these things

1. **NEVER configure CORS only in the Lambda handler.** CORS must
   be configured at the function URL level via the `--cors`
   parameter. Handler-level CORS headers alone will fail browser
   preflight requests because the function URL itself does not return
   CORS headers for OPTIONS.

2. **NEVER use NONE auth for internal or authenticated endpoints.**
   NONE auth is public internet with zero authentication. Anyone
   with the URL can invoke it. Use AWS_IAM auth for anything that
   should not be publicly accessible.

3. **NEVER assume the 15-second timeout matches the function
   timeout.** Function URL invocations are capped at 15 seconds
   regardless of the function's configured timeout. Long-running
   workloads cannot be served synchronously via function URLs.

4. **NEVER switch invoke mode without updating the handler.**
   BUFFERED and RESPONSE_STREAM require different handler signatures.
   Switching without updating the handler produces a runtime error.

5. **NEVER assume the function URL follows a new alias.** Function
   URLs point at `$LATEST` by default. To point at a custom alias
   (e.g., `prod`), you must update the function URL config with
   `--qualifier prod`.

6. **NEVER expect CloudFront to sign IAM-authenticated function URL
   requests natively.** CloudFront cannot sign SigV4 requests for
   Lambda function URLs. Use NONE auth + WAF + app-level auth, or a
   Lambda@Edge / CloudFront Function to sign requests.

7. **NEVER create a function URL on a Lambda@Edge function.**
   Function URLs do not support Lambda@Edge. The function must be a
   standard regional Lambda function.

8. **NEVER forget to set up CloudWatch alarms for Url5xx.** Function
   URL errors (5xx) indicate handler failures or timeouts. Without
   alarms, errors go unnoticed. Set up a CloudWatch alarm on the
   Url5xx metric.

9. **NEVER assume function URLs replace API Gateway for all use
   cases.** Function URLs do not support usage plans, API keys,
   request validation, throttling (beyond account-level Lambda
   throttles), or built-in WebSocket support. For these features,
   use API Gateway.

10. **NEVER ignore cold start for latency-sensitive workloads.**
    Cold starts add 100ms–several seconds to the first invocation.
    Use provisioned concurrency or RESPONSE_STREAM mode to mitigate.

## Output format

```text
LAMBDA_FUNCTION_URL: https://<id>.lambda-url.<region>.on.aws/
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Lambda function: <function-name> (exists, runtime: <runtime>)
  [✓|✗] Auth mode: AWS_IAM | NONE
  [✓|✗] Invoke mode: BUFFERED | RESPONSE_STREAM
  [✓|✗] CORS: AllowOrigins=<list>, AllowMethods=<list>, AllowHeaders=<list>, ExposeHeaders=<list>, MaxAgeSeconds=<n>
  [✓|✗] Timeout check: function timeout <n>s | function URL cap 15s (warn if function timeout > 15s)
  [✓|✗] Dual-stack: IPv4 + IPv6 (automatic)
  [✓|✗] Qualifier: $LATEST | <alias>
  [✓|✗] Resource-based policy (if AWS_IAM): <statement-id> grants lambda:InvokeFunctionUrl to <principal>
  [✓|✗] CloudWatch metrics: UrlRequests, Url4xx, Url5xx, UrlLatency (automatic)
  [✓|✗] CloudFront custom domain (if applicable): <domain> → <origin>
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws lambda get-function-url-config --function-name <name> --region <region>
  aws lambda get-policy --function-name <name> --region <region>
  aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Url5xx --dimensions Name=FunctionName,Value=<name> --start-time <time> --end-time <time> --period 300 --statistics Sum --region <region>
```

### Worked example — BUFFERED with IAM auth and CORS

```text
LAMBDA_FUNCTION_URL: https://abc123def456.lambda-url.us-east-1.on.aws/
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Lambda function: my-api-handler (exists, runtime: nodejs20.x)
  [✓] Auth mode: AWS_IAM
  [✓] Invoke mode: BUFFERED
  [✓] CORS: AllowOrigins=["https://app.example.com"], AllowMethods=["GET","POST"], AllowHeaders=["content-type","authorization"], ExposeHeaders=["x-request-id"], MaxAgeSeconds=86400
  [✓] Timeout check: function timeout 10s (within 15s function URL cap)
  [✓] Dual-stack: IPv4 + IPv6 (automatic)
  [✓] Qualifier: $LATEST
  [✓] Resource-based policy: statement function-url-invoke grants lambda:InvokeFunctionUrl to arn:aws:iam::111122223333:user/alice
  [✓] CloudWatch metrics: UrlRequests, Url4xx, Url5xx, UrlLatency (automatic)
  [✓] Tags: Environment=production, Service=api
VERIFICATION_COMMANDS:
  aws lambda get-function-url-config --function-name my-api-handler --region us-east-1
  aws lambda get-policy --function-name my-api-handler --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Url5xx --dimensions Name=FunctionName,Value=my-api-handler --start-time 2026-08-11T00:00:00Z --end-time 2026-08-11T01:00:00Z --period 300 --statistics Sum --region us-east-1
```

### Worked example — RESPONSE_STREAM with NONE auth and CloudFront

```text
LAMBDA_FUNCTION_URL: https://xyz789abc012.lambda-url.us-east-1.on.aws/
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Lambda function: my-streaming-handler (exists, runtime: nodejs20.x)
  [✓] Auth mode: NONE (public endpoint — WAF + app-level auth)
  [✓] Invoke mode: RESPONSE_STREAM
  [✓] CORS: AllowOrigins=["*"], AllowMethods=["GET","POST"], AllowHeaders=["content-type"], MaxAgeSeconds=3600
  [✓] Timeout check: function timeout 15s (at function URL cap)
  [✓] Dual-stack: IPv4 + IPv6 (automatic)
  [✓] Qualifier: prod
  [✓] CloudFront custom domain: stream.example.com → https://xyz789abc012.lambda-url.us-east-1.on.aws/
  [✓] CloudWatch metrics: UrlRequests, Url4xx, Url5xx, UrlLatency (automatic)
  [✓] Tags: Environment=production, Service=streaming-api
VERIFICATION_COMMANDS:
  aws lambda get-function-url-config --function-name my-streaming-handler --qualifier prod --region us-east-1
  aws cloudfront get-distribution-config --id <distribution-id> --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name UrlLatency --dimensions Name=FunctionName,Value=my-streaming-handler --start-time 2026-08-11T00:00:00Z --end-time 2026-08-11T01:00:00Z --period 300 --statistics Average --region us-east-1
```

## Error handling

### Browser preflight (OPTIONS) fails with CORS error
- The function URL does not have CORS configured. Add the `--cors`
  parameter to the function URL config with AllowOrigins,
  AllowMethods, and AllowHeaders. CORS is at the function URL level,
  not the Lambda function level.

### Function URL returns 403 Forbidden
- If auth type is AWS_IAM, the caller's request is not properly
  signed with SigV4, or the resource-based policy does not grant
  `lambda:InvokeFunctionUrl` to the caller. Verify the policy with
  `aws lambda get-policy`.

### Function URL returns 504 Timeout
- The handler exceeded the 15-second function URL invocation cap.
  Reduce handler execution time, use RESPONSE_STREAM mode to start
  streaming earlier, or move long-running work to async invocation.

### RESPONSE_STREAM returns a runtime error
- The handler signature does not match RESPONSE_STREAM expectations.
  Ensure the handler uses `awslambda.streamifyResponse` (Node.js) or
  the equivalent streaming wrapper for the runtime. Verify the
  runtime supports streaming.

### Function URL points to wrong alias
- The function URL is still on `$LATEST`. Update with
  `--qualifier <alias>` to point at the intended alias.

### CloudFront returns 502/503
- The origin (function URL) is unreachable or returning errors.
  Verify the function URL works directly first. Check CloudFront
  origin settings — the origin must be the full function URL
  hostname.

## Domain

AWS CloudOps / AWS Lambda Function URL Provisioning & HTTP Endpoint
Management.

## AWS documentation

- **Lambda Function URLs** — https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html
- **Creating a function URL** — https://docs.aws.amazon.com/lambda/latest/dg/urls-configuration.html
- **Function URL auth** — https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html
- **Function URL CORS** — https://docs.aws.amazon.com/lambda/latest/dg/urls-cors.html
- **Function URL invoke modes** — https://docs.aws.amazon.com/lambda/latest/dg/urls-invocation.html
- **Response streaming** — https://docs.aws.amazon.com/lambda/latest/dg/response-streaming.html
- **Function URL metrics** — https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics.html#function-url-metrics
- **CloudFront + Lambda URL** — https://docs.aws.amazon.com/lambda/latest/dg/urls-tutorial.html
- **Lambda pricing** — https://aws.amazon.com/lambda/pricing/
