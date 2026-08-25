---
name: lambda-function-url-deployer
description: 'Provisions AWS Lambda Function URLs with production defaults: auth mode (AWS_IAM vs NONE), CORS configuration (allowOrigins, allowMethods, allowHeaders, exposeHeaders, maxAgeSeconds), invoke mode (BUFFERED vs RESPONSE_STREAM), 15-second timeout limit for function URL invocations, dual-stack IPv4/IPv6 endpoints, $LATEST alias constraint (cannot attach to a custom alias without UpdateFunctionUrl), CloudWatch metrics (UrlRequests, Url4xx, Url5xx, UrlLatency), cold start impact on first-byte latency, custom domain via CloudFront + Lambda URL, and pricing parity with standard Lambda invocations. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating a Lambda function URL, configuring CORS on a function URL, enabling response streaming, setting up IAM-authenticated function. Triggers: create lambda function url, configure cors on function url, enable response streaming lambda, lambda function url iam auth, lambda url cloudfront custom domain, lambda function url buffered vs...'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with lambda access. Works with Terraform aws_lambda_function_url resource and CloudFormation AWS::Lambda::Url templates.'
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, lambda, lambda-function-url, cloudops, deploy, compute, provisioning, cors, streaming, iam, cloudfront, dual-stack
  dependencies: aws-orchestrator
  keywords: aws, lambda, function url, cloudops, deploy, provisioning, cors, response streaming, iam auth, dual-stack, cloudfront, invoke mode, buffered, response_stream
  when_to_use: Invoke when the user wants to create a Lambda Function URL, configure CORS on an existing function URL, switch invoke mode between BUFFERED and RESPONSE_STREAM, set up IAM-authenticated vs public (NONE auth) function URLs, place a custom domain (CloudFront) in front of a function URL, or monitor function URL CloudWatch metrics. Do NOT invoke for API Gateway HTTP/REST APIs (use apigateway skills), Lambda@Edge (use lambda-at-edge skills), or Application Load Balancer targets (use alb skills).
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

Four-misconception catalog moved to `references/advanced-patterns.md` —
see "Mindset — four misconceptions".

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

CORS-row walkthrough and cross-dependency gotchas moved to
`references/advanced-patterns.md` (dependency-graph extras).

## Expert heuristic: RESPONSE_STREAM first byte advantage

Timeline comparison and workload guidance moved to
`references/advanced-patterns.md` (RESPONSE_STREAM heuristic).

## Expert heuristic: CORS is at the function URL level

WRONG-vs-CORRECT CORS pattern moved to `references/cors-and-auth.md`;
summary: CORS is set on the URL config via `--cors`.

## Expert heuristic: NONE auth is public internet

NONE vs AWS_IAM invocation flows moved to `references/advanced-patterns.md`;
summary: NONE auth = public internet, no security boundary.

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

URL response format, verify CLI, and creation mistake moved to
`references/advanced-patterns.md` + `references/diagnostic-commands.md`.

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

add-permission resource-policy CLI and cross-account notes moved to
`references/cors-and-auth.md` (Step 2 detail).

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

Create-with-CORS and update-CORS CLI sequences moved to
`references/cors-and-auth.md` (Step 3 detail).

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

BUFFERED/RESPONSE_STREAM handler code and streaming create CLI moved
to `references/streaming-and-cloudfront.md` (Step 4 detail).

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

Timeout verification CLI moved to `references/diagnostic-commands.md`.
The 15-second cap itself is a hard rule (see NEVER #3).

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

Dual-stack implications (IPv6 clients, SG/WAF, CloudFront IPv6) moved
to `references/advanced-patterns.md` (Step 6 detail).

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

Qualifier verification CLI moved to `references/diagnostic-commands.md`.
Key rule: update with `--qualifier <alias>` or the URL stays on $LATEST.

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

Metric-query and 5xx-alarm CLI moved to `references/diagnostic-commands.md`
(Step 8 detail). Metric table above is authoritative.

## Step 9 — Cold start impact

Cold-start timeline, mitigations, and provisioned-concurrency CLI moved
to `references/advanced-patterns.md` (Step 9 detail).

## Step 10 — Custom domain via CloudFront + Lambda URL

Lambda Function URLs do not natively support custom domains. To use
a custom domain (e.g., `api.example.com`), place a CloudFront
distribution in front of the function URL.

CloudFront diagram, distribution CLI, critical considerations, and ACM
setup moved to `references/streaming-and-cloudfront.md` (Step 10 detail).

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

Feature list moved to `references/advanced-patterns.md` —
see "Step 12 — recent features".

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

This secondary worked example moved to `references/worked-examples.md`.
The BUFFERED/IAM example above is the primary shape to copy.

## Error handling

Error symptom catalog (CORS preflight, 403, 504, runtime error, wrong
alias, CloudFront 502/503) moved to `references/error-handling.md`.

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
## References (load on demand)

- [advanced-patterns.md](references/advanced-patterns.md) — misconceptions,
  dependency-graph extras, expert heuristics, per-step deep dives
  (cold start, dual-stack), recent features.
- [diagnostic-commands.md](references/diagnostic-commands.md) — URL
  creation/qualifier/timeout verification, CloudWatch metrics CLI.
- [worked-examples.md](references/worked-examples.md) — secondary
  RESPONSE_STREAM + CloudFront worked example.
- [error-handling.md](references/error-handling.md) — error symptom
  catalog and fixes.

