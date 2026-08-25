# Advanced patterns - API Gateway REST Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset

**One-line takeaway:** a production REST API is not "a method on a path"
— it is a **layered security and contract model** where every method
has an explicit authorization, every integration has a typed contract
(mapping templates or proxy), every stage has a deployment snapshot with
throttling, and every consumer has a usage plan. The route-to-Lambda is
the least interesting part; the **authorization model, throttle budget,
and deployment discipline** determine blast radius and uptime.

Three facts make API Gateway provisioning different from "expose a
Lambda over HTTP":

- **Stage + Deployment is a snapshot model, not live editing.** A
  deployment is an immutable snapshot of the API configuration. The
  stage points to a deployment. Modifying methods/resources without
  `create-deployment` leaves the OLD configuration live. Many operators
  change auth type, see "success" in the console, and walk away — the
  insecure old version is still serving because no deployment was created.

- **API keys are NOT authentication.** `apiKeyRequired: true` on a method
  with `authorizationType: NONE` provides ZERO access control. API keys
  are identification tokens for usage plans (throttling/quotas) — they are
  transmitted in cleartext (`x-api-key`), shareable, and extractable from
  client code. Authentication comes from `AWS_IAM`, `COGNITO_USER_POOLS`,
  or a `CUSTOM` Lambda authorizer.

- **REST API (v1) and HTTP API (v2) are different products, not versions.**
  HTTP API is cheaper, simpler, and faster — but lacks mapping templates,
  usage plans, API keys, resource policies, and EDGE endpoint type. REST
  API supports the full feature surface. Choose based on requirements, not
  on "newer is better." For Lambda proxy with JWT auth, HTTP API is often
  the right choice. For per-consumer rate limiting or SOAP-style XML
  transforms, REST API is required.

## Step 0: Expert knowledge — non-obvious API Gateway behaviors that change the plan

- **Changes are not live until `create-deployment`.** Resources, methods,
  integrations, and authorizers are configuration. The deployment is the
  snapshot that goes live. Operators frequently modify auth and walk away
  without deploying — the old (often insecure) config keeps serving.
  Always emit `create-deployment` as the final command.

- **API keys are NOT authentication.** `apiKeyRequired: true` gates usage
  plan enforcement. `authorizationType: NONE` + `apiKeyRequired: true` is
  PUBLIC_NO_AUTH. The key is in the `x-api-key` header in cleartext. Use
  AWS_IAM, COGNITO_USER_POOLS, or a Lambda authorizer for real auth.

- **ANY method covers all HTTP verbs.** ANY maps to GET, POST, PUT, PATCH,
  DELETE, HEAD, OPTIONS simultaneously. ANY + NONE auth is the most
  dangerous method configuration — it exposes every verb including
  destructive ones (DELETE, PUT) without authentication.

- **`{proxy+}` is a catch-all greedy path.** ANY on `{proxy+}` catches
  every sub-path. If this combination has NONE auth, every route beneath
  is exposed. Use `{proxy+}` carefully and always with an authorizer.

- **Usage plan without API keys is dormant.** A plan with zero associated
  keys cannot enforce throttling or quotas. Always link at least one API
  key after creating the plan.

- **Account-level default throttle is shared across all APIs in the region.**
  Default is 10,000 rps / 5,000 burst. One abused API can exhaust the
  budget and 429 every other API in the region. Always create a usage plan
  with explicit per-consumer throttles.

- **EDGE endpoint hides the client IP behind CloudFront.** `aws:SourceIp`
  in a resource policy matches CloudFront edge IPs, not client IPs. For
  client-IP restrictions on EDGE APIs, use WAF or a Lambda authorizer
  reading `x-forwarded-for`.

- **WAF rate-based rules count per IP, not per API key.** One attacker
  rotating across 100 IPs with 100 API keys bypasses a 2,000-req/5-min
  IP rule. For per-key limiting, only usage-plan throttling is effective.

- **Mapping templates are Velocity (VTL).** REST API supports
  request/response mapping templates for transformation between client
  and integration format. HTTP API does NOT support mapping templates —
  you get the raw request or use a Lambda to transform.

- **VPC Link target must be an NLB.** The NLB must have target groups in
  the API's region. ALB is NOT directly supported as a VPC Link target —
  front the ALB with an NLB, or use an HTTP integration with the ALB DNS.

- **Stage variables enable per-stage config.** Use stage variables to
  point at different Lambda function versions, endpoint URLs, or feature
  flags per stage (prod, staging, dev). Reference in integration as
  `${stageVariables.functionName}`.

- **Canary deployment shifts a percentage of traffic.** Configure the
  canary to send e.g., 10% of traffic to the new deployment; 90% stays on
  the stable deployment. Promote by increasing to 100% when metrics are
  green.

- **Access logging uses CloudWatch Logs with JSON format.** Configure
  `$context` variables (requestId, accountId, stage, httpMethod, status,
  responseLatency, sourceIp, errorMessage, authorizer error). JSON format
  enables Athena/CloudWatch Logs Insights queries.

- **Custom domain requires ACM cert + base path mapping.** The cert must
  cover the domain. The base path mapping determines which API stage a
  path maps to (e.g., `api.example.com/v1` → API-1 prod stage).


## Edge-case handling

- **Stage without deployment.** A stage with no current deployment serves
  nothing. Always create the deployment first, then point the stage at it.

- **Lambda function in different region.** API Gateway integrations can
  target Lambda in another region, but this adds latency and is an
  anti-pattern. Deploy function in the same region as the API.

- **WAF rate-based rule with rotating attackers.** IP-based rate limiting
  does not correlate with API keys. For per-key limiting, rely on usage
  plan throttles, not WAF.

- **Cognito authorizer caching.** Default TTL is 300 seconds. A revoked
  token may still work for up to 5 minutes. Lower the TTL for sensitive
  APIs, but expect higher Cognito invocation costs.

- **Edge endpoint with resource policy IP conditions.** `aws:SourceIp`
  matches CloudFront edge IPs, not client IPs. Use WAF or Lambda
  authorizer for client-IP restrictions on EDGE APIs.

- **HTTP API without authorizer.** An HTTP API with no JWT or IAM
  authorizer is fully public. Treat as equivalent to REST API with
  `authorizationType: NONE`.


## Recent AWS features (2024-2026)

- **HTTP API mTLS:** HTTP APIs support mutual TLS via custom domain names.
  Use for B2B APIs with strict client certificate requirements.

- **VPC Lattice integration:** HTTP APIs can integrate with VPC Lattice
  as a private integration. A Lattice-backed API may not appear in
  standard VPC security group audits — check Lattice auth policies.

- **OpenAPI 3.1 support:** REST and HTTP APIs support OpenAPI 3.1 import.
  Auth configurations can be imported from external specs. Verify the
  imported `x-amazon-apigateway-*` extensions match intended security.

- **API Gateway v2 OpenAPI importer:** Enhanced importer for HTTP APIs
  with better JWT authorizer and route mapping support.

- **Canary deployment improvements:** Stage canary now supports weighted
  logging — canary vs stable traffic split is visible in CloudWatch
  metrics dimensions.

- **WebSocket APIs (stable):** API Gateway WebSocket APIs are GA and
  integrate with Lambda for real-time bidirectional workloads. Not
  covered by this skill (REST/HTTP only).


