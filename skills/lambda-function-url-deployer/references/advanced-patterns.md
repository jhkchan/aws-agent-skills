# Advanced patterns — lambda-function-url-deployer

> Content moved verbatim from SKILL.md during progressive-disclosure
> restructuring. Load on demand.

## Mindset — four misconceptions

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

## Configuration dependency graph — extras

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

## Step 1 detail: function URL response

The response includes the `FunctionUrl` — the HTTPS endpoint:

```text
https://<id>.lambda-url.<region>.on.aws/
```

## Step 1 detail: common mistake

**Common mistake:** trying to create a function URL on a function
that does not exist yet. The function must be created first.

## Step 6 detail: dual-stack implications

**Implications:**
- Clients on IPv6-only networks (rare but growing) can reach
  function URLs without NAT64 or other translation.
- Security groups and WAF rules must account for both IPv4 and IPv6
  source addresses if filtering by IP.
- CloudFront in front of a function URL connects via IPv4 by
  default. For IPv6 client support through CloudFront, enable IPv6
  on the CloudFront distribution.

## Step 9 detail: cold start impact and mitigations

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

## Step 12: recent features (2023-2026)

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

