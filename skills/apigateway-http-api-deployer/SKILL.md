---
name: apigateway-http-api-deployer
description: >-
  Provisions production-grade API Gateway HTTP APIs (v2) with routes
  (ANY, GET, POST, {proxy+} greedy), integration targets (Lambda proxy
  AWS_PROXY, HTTP proxy, VPC link private integration, Step Functions
  START_EXECUTION, SQS SendMessage, Kinesis PutRecord), JWT authorizer
  backed by OpenID Connect / Cognito issuer, CORS configuration with
  preflight handling, JSON access logging to CloudWatch with $context
  variables, stage auto-deploy for continuous deployment, custom domain
  via ACM with API mapping, and WAFv2 REGIONAL Web ACL association.
  Emits a READY_TO_DEPLOY checklist and ordered aws apigatewayv2
  commands. Use when provisioning an HTTP API, configuring JWT/OIDC
  authorizers, setting up CORS, integrating Step Functions / SQS /
  Kinesis from HTTP API, deploying VPC link private integrations, or
  enabling auto-deploy stages.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline architecture
  planning. Live deployment uses aws apigatewayv2 create-api,
  create-route, create-integration, create-authorizer, create-stage,
  update-stage, create-domain-name, create-api-mapping, update-route,
  and aws wafv2 associate-web-acl (AWS CLI v2, SSO or key-based
  credentials).
keywords:
  - API Gateway
  - HTTP API
  - API Gateway v2
  - apigatewayv2
  - route
  - ANY method
  - proxy path
  - Lambda proxy
  - AWS_PROXY
  - HTTP proxy
  - HTTP_PROXY
  - VPC link
  - private integration
  - Step Functions
  - START_EXECUTION
  - SQS integration
  - Kinesis integration
  - JWT authorizer
  - OpenID Connect
  - OIDC
  - Cognito
  - CORS
  - preflight
  - access logging
  - auto-deploy
  - stage
  - custom domain
  - ACM
  - API mapping
  - WAFv2
  - Web ACL
tags: [apigateway, app-integration, deploy, http-api, apigatewayv2, lambda-proxy, jwt-authorizer, oidc, cors, vpc-link, step-functions, auto-deploy, access-logging, custom-domain, waf]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Provisioning a new API Gateway HTTP API (v2) for production,
    configuring Lambda proxy (AWS_PROXY) or HTTP_PROXY integrations,
    setting up a JWT authorizer backed by OpenID Connect or Cognito,
    enabling CORS with preflight, integrating Step Functions / SQS /
    Kinesis directly from HTTP API, deploying private integrations via
    VPC link to an NLB, enabling stage auto-deploy for continuous
    deployment, configuring JSON access logging, mapping a custom domain
    name via ACM, or associating a WAFv2 REGIONAL Web ACL.
  activation_triggers:
    - "create an HTTP API"
    - "provision API Gateway v2"
    - "API Gateway HTTP API"
    - "Lambda proxy HTTP API"
    - "JWT authorizer HTTP API"
    - "OIDC authorizer API Gateway"
    - "CORS configuration API Gateway"
    - "Step Functions HTTP API"
    - "SQS API Gateway integration"
    - "Kinesis API Gateway integration"
    - "VPC link private integration"
    - "auto-deploy stage"
    - "API Gateway custom domain"
    - "REST to HTTP migration"
  invocation_schema: >-
    Input shape (one of): (a) a deployment specification including
    routes (method + path, including ANY and {proxy+}), integration
    targets (Lambda, HTTP_PROXY, VPC_LINK, STEP_FUNCTION, SQS, KINESIS),
    JWT authorizer issuer/audience, CORS requirements, logging,
    auto-deploy, custom domain, WAF; (b) a partial spec for interactive
    refinement; (c) an existing HTTP API ID for architecture review.
    Output shape: { API_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[],
    FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ {
    READY_TO_DEPLOY, PREREQUISITES_MISSING, ERROR }.
---

# API Gateway HTTP API Deployer

## Mindset

**One-line takeaway:** an HTTP API (v2) is not "a cheaper REST API"
— it is a **simpler, faster, event-shaped routing product** where every
route binds directly to a typed integration (Lambda proxy, HTTP proxy,
VPC link, Step Functions, SQS, Kinesis), authorization is JWT-only,
there are no mapping templates, and stages default to **auto-deploy**.
The route table and the JWT authorizer are the load-bearing decisions;
CORS, logging, and custom domain are deterministic follow-ons.

Three facts make HTTP API (v2) provisioning different from REST API
(v1):

- **Routes are flat `(method, path)` pairs, not a resource tree.** A
  route is `$default`, `ANY /{proxy+}`, `GET /users`, or `POST
  /orders`. No resources, no methods on resources, no nested hierarchy.
  The greedy `{proxy+}` catches every sub-path — combined with `ANY`
  it is the catch-all that makes exposure mistakes trivial.

- **Integrations are typed targets, not mapping-template contracts.**
  `AWS_PROXY` (Lambda proxy) is the default, but HTTP API also exposes
  `HTTP_PROXY`, `HTTP`, and direct AWS-service integrations including
  `STEP_FUNCTION` (`START_EXECUTION` / `START_SYNC_EXECUTION`), `SQS`
  (`SendMessage`), and `KINESIS` (`PutRecord` / `PutRecords`). These
  run **without a Lambda in the path**, lowering latency and cost —
  but the request/response shape is fixed by API Gateway.

- **JWT is the only user-facing authorizer; CORS and auto-deploy are
  first-class.** HTTP API supports `JWT` (OpenID Connect / Cognito
  issuer) and `AWS_IAM`. There is no `COGNITO_USER_POOLS` type and no
  Lambda authorizer — JWT is the user-facing contract. CORS is set at
  the API level. Stages default to `auto-deploy: true`, so every route
  change is live within seconds — there is no `create-deployment` step.

## Quick reference — deployment checklist

| Dimension | Requirement | Step |
|---|---|---|
| API type | HTTP (v2) — confirm feature fit (no usage plans, no mapping templates) | Step 1 |
| Routes | Flat `(method, path)` list including ANY, GET, POST, `{proxy+}` | Step 2 |
| Integration | Lambda proxy, HTTP proxy, VPC link, Step Functions, SQS, Kinesis | Step 3 |
| Authorization | JWT (OIDC issuer + audience) or AWS_IAM (NONE only for public) | Step 4 |
| CORS | API-level allow-origins, methods, headers, preflight max-age | Step 5 |
| Stage auto-deploy | `auto-deploy: true` (default) or pinned to a deployment | Step 6 |
| Access logging | JSON `$context` to CloudWatch Logs | Step 7 |
| Custom domain | ACM cert + API mapping (no base path) | Step 8 |
| WAFv2 Web ACL | REGIONAL scope, associated with stage | Step 9 |
| Throttle / quotas | Per-route throttle + account default | Step 10 |

## Pre-flight: deployment specification gate

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment** — proceeding with an invalid
spec produces a non-functional or insecure API.

**Live-account pre-flight checks (skip if doing offline plan):**
1. Verify IAM permissions for `apigatewayv2:CreateApi`, `CreateRoute`,
   `CreateIntegration`, `CreateAuthorizer`, `CreateStage`,
   `UpdateStage`, `CreateDomainName`, `CreateApiMapping`,
   `UpdateRoute`, and `wafv2:CreateWebACL`, `wafv2:AssociateWebACL`.
2. For Lambda integrations, verify the function exists in the same
   region and grant `lambda:InvokeFunction` to the
   `apigateway.amazonaws.com` principal scoped to the API's source ARN.
3. For VPC link, verify the NLB exists and target groups span multiple
   AZs. **NLB only — ALB is not a valid target.**
4. For JWT authorizers, verify the OIDC issuer returns a valid OpenID
   configuration with a JWKS URI, and that the audience claim matches
   an issued `client_id`.
5. For custom domains, verify the ACM certificate is `ISSUED` in the
   API's region (`REGIONAL` only — HTTP API does not support EDGE).

| Attribute | Value | Effect on plan |
|---|---|---|
| `protocolType` | `HTTP` | Required. HTTP API is its own product, not a REST API mode. |
| `routeKey` | `METHOD /path` | Flat route. `ANY /{proxy+}` is the catch-all greedy route. |
| Integration type | `AWS_PROXY` / `HTTP_PROXY` / `HTTP` / `AWS` (Step Functions / SQS / Kinesis) | Determines the request/response contract. |
| Authorization | `JWT` | OpenID Connect issuer + audience. The only user-facing authorizer. |
| Authorization | `AWS_IAM` | Sigv4. Service-to-service. |
| Authorization | `NONE` | Public. Acceptable ONLY for health checks or genuinely public routes. |
| `auto-deploy` | `true` / `false` | Default `true` on `$default` stage. Pins to deployment if `false`. |

**If the deployment spec is incomplete** (missing routes, integration
type, or JWT issuer for an authorized route), output:

```text
API_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce a deployment plan without <field> — the resulting API
would be non-functional or insecure.
REQUIRED:
  - routes (method + path, including ANY / {proxy+})
  - integration_type (AWS_PROXY / HTTP_PROXY / VPC_LINK / STEP_FUNCTION / SQS / KINESIS)
  - authorization (JWT / AWS_IAM / NONE) with issuer + audience for JWT
```

## STRICT output contract

When this skill is invoked with an HTTP API provisioning request
(routes, integration targets, JWT authorizer, CORS, logging, custom
domain, or a partial configuration), the agent MUST respond with the
deployment plan defined in the "Output format" section using the
literal all-caps labels `API_SPEC:`, `VERDICT:`, `ARCHITECTURE:`,
`CHECKLIST:`, `FINDINGS:`, and `DEPLOY_COMMANDS:`. Do NOT preface the
block with prose, headings, or disclaimers — emit it as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

If any prerequisite is missing, the verdict is
`PREREQUISITES_MISSING` with a specific gap citation in the checklist
(marked `[✗]`), and `READY_TO_DEPLOY` MUST NOT also appear. The two
verdicts are mutually exclusive.

## Quick navigation

| Section | When to read |
|---|---|
| Pre-flight specification gate | Always — verify before planning |
| Step 0 — Expert heuristic: auto-deploy vs pinned deployments | Choosing stage mode |
| Step 1 — HTTP API vs REST API fit | Boundary call |
| Step 2 — Route model (ANY, GET, POST, {proxy+}) | Route design |
| Step 3 — Integration targets (Lambda / HTTP / VPC / SFN / SQS / Kinesis) | Backend wiring |
| Step 4 — JWT authorizer (OIDC issuer + audience) | Authorization |
| Step 5 — CORS configuration | Browser clients |
| Step 6 — Stage auto-deploy | Continuous deployment |
| Step 7 — Access logging | Observability |
| Step 8 — Custom domain (API mapping) | Vanity URL |
| Step 9 — WAFv2 Web ACL | Edge security |
| Step 10 — Throttle and quotas | Abuse prevention |
| NEVER do these things | Review before signing off |
| Output format | The literal plan template |
| references/integrations-and-routes-reference.md | Per-integration contract detail |
| references/jwt-cors-domain-auto-deploy-reference.md | Authorizer + CORS + auto-deploy deep dive |

## Process — Architecture planning (apply in order, produce deployment plan)

### Step 0: Expert heuristic — auto-deploy vs pinned deployment stages

HTTP API stages behave **opposite** to REST API stages. A baseline
model trained on REST API assumes you must call `create-deployment` for
any change to go live. On HTTP API, **the `$default` stage has
`auto-deploy: true` by default**, meaning every route, integration, and
authorizer change is live within seconds without a deployment call.

```text
create-api → $default stage auto-created with auto-deploy: true
operator adds / modifies a route or integration
  → API Gateway evaluates against $default
  → deployment auto-created within seconds
  → change is LIVE
if auto-deploy: false (pinned stage)
  → changes accumulate but are NOT served
  → must create-deployment + update-stage to pin
```

**Implications:**
- For continuous-deployment pipelines (CodePipeline, SAM, CloudFormation
  with `AWS::ApiGatewayV2::Deployment`), leave `auto-deploy: true` and
  let the framework manage routes. Adding a synthetic
  `AWS::ApiGatewayV2::Deployment` resource on top races with auto-deploy
  and produces drift.
- For gated releases, set `auto-deploy: false`, then use
  `create-deployment` and `update-stage` to swap versions.
- A pinned stage with no current deployment serves **404** for every
  route — the routes exist in configuration but the stage has no
  snapshot. Always emit a deployment when pinning.

### Step 1: HTTP API (v2) vs REST API (v1) — feature fit

| Dimension | HTTP API (v2) | REST API (v1) |
|---|---|---|
| Cost per million requests | $1.00 | $3.50 |
| Latency | ~30% lower | Higher |
| Mapping templates (VTL) | No | Yes |
| Usage plans + API keys | No | Yes |
| Resource policies | No | Yes |
| Authorization | JWT, AWS_IAM | AWS_IAM, COGNITO_USER_POOLS, CUSTOM |
| EDGE endpoint | No | Yes |
| PRIVATE endpoint | Yes (VPC link / Lattice) | Yes |
| WAF association | Yes | Yes |
| Custom domains | Yes (REGIONAL) | Yes (EDGE + REGIONAL) |
| Stage model | `auto-deploy` by default | `create-deployment` required |
| Direct AWS integrations | Step Functions, SQS, Kinesis | Broader (DynamoDB, SNS, SQS, Kinesis, Step Functions) |
| Canary | No (use stage swap) | Yes |

**Decision rule — pick HTTP API when ALL of these hold:**
- Auth is JWT (OIDC/Cognito) or AWS_IAM.
- No mapping templates required.
- No per-consumer usage plans or API keys required.
- No EDGE endpoint required.

Otherwise, REST API is the right product. See the
`apigateway-rest-deployer` skill for the v1 plan.

### Step 2: Route model (ANY, GET, POST, {proxy+})

Routes are flat `(method, path)` pairs. The greedy `{proxy+}` matches
one or more path segments.

```text
$default                          → catch-all for ANY method and any path
ANY /{proxy+}                     → greedy route (every method, every sub-path)
GET /health                       → exact route
GET /users                        → exact route
POST /users                       → exact route
GET /users/{userId}               → path parameter
ANY /users/{proxy+}               → greedy under /users
```

**`$default` vs `ANY /{proxy+}`:** `$default` is the API-level fallback
for any unmatched route. `ANY /{proxy+}` is a route that matches the
greedy pattern. `$default` is the only route that handles `ANY` for all
paths without appearing in the route table.

**CORS preflight:** when CORS is enabled, API Gateway synthesizes
`OPTIONS` responses for routes with matching origins. You do NOT add
`OPTIONS` routes manually. An explicit `OPTIONS /path` route overrides
the synthesized response — only do this for non-standard headers.

**ANY + NONE auth is the most dangerous route configuration in HTTP
API.** `ANY /{proxy+}` with `authorizationType: NONE` exposes every
method (GET, POST, PUT, PATCH, DELETE) on every sub-path without auth.
Always bind an authorizer to catch-all routes.

```bash
aws apigatewayv2 create-route --api-id <id> \
  --route-key "POST /users" \
  --target integrations/<integration-id> \
  --authorizer-id <authorizer-id> \
  --authorization-type JWT
```

### Step 3: Integration targets

| Type | Subtype | When to use |
|---|---|---|
| `AWS_PROXY` | Lambda proxy | Default for Lambda. Full request as JSON event. Lambda returns `{statusCode, headers, body}`. |
| `HTTP_PROXY` | HTTP pass-through | External HTTP endpoint, no transform. VPC link connections use this. |
| `HTTP` | HTTP with transform | External HTTP endpoint with header/path rewrite (limited). |
| `AWS` | `STEP_FUNCTION` (`START_EXECUTION` / `START_SYNC_EXECUTION`) | Trigger Express Workflow synchronously or Standard async without Lambda. |
| `AWS` | `SQS` (`SendMessage`) | Drop message to SQS queue directly. |
| `AWS` | `KINESIS` (`PutRecord` / `PutRecords`) | Stream record to Kinesis directly. |

**Lambda proxy:**
```bash
aws apigatewayv2 create-integration --api-id <id> \
  --integration-type AWS_PROXY --integration-method POST \
  --integration-uri arn:aws:apigateway:<region>:lambda:path/2015-03-31/functions/arn:aws:lambda:<region>:<account>:function:<name>/invocations

aws lambda add-permission --function-name <name> \
  --statement-id apigw-v2-invoke --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn arn:aws:execute-api:<region>:<account>:<api-id>/*/POST/users
```

**HTTP proxy via VPC link:**
```bash
aws apigatewayv2 create-vpc-link --name prod-nlb-link \
  --subnet-ids subnet-abc subnet-def --security-group-ids sg-xyz

aws apigatewayv2 create-integration --api-id <id> \
  --integration-type HTTP_PROXY --integration-method ANY \
  --integration-uri https://<nlb-dns>/api \
  --connection-id <vpc-link-id> --connection-type VPC_LINK
```

**Step Functions START_SYNC_EXECUTION (direct, no Lambda):** use
`StartSyncExecution` for Express Workflows (caller needs the result
inline, 5s ceiling); `StartExecution` for Standard Workflows (async —
API returns the execution ARN immediately).
```bash
aws apigatewayv2 create-integration --api-id <id> \
  --integration-type AWS --integration-method POST \
  --integration-subtype STEP_FUNCTION \
  --request-parameters '{"StateMachineArn":"arn:aws:states:<region>:<account>:stateMachine:<name>","Action":"StartSyncExecution","Input":"$request.body"}'
```

**SQS SendMessage (direct):** uses `credentials-arn` (IAM role trusting
`apigateway.amazonaws.com`) with `MessageBody` mapped from the request
body.

**Kinesis PutRecord (direct):** uses `credentials-arn` with `Data`
mapped from the request body and `PartitionKey` mapped from
`$context.requestId` (or a JWT claim for tenant-partitioned streams).

Direct AWS integrations need a `credentials-arn` (an IAM role trusting
`apigateway.amazonaws.com` with permission to call the target service).
This role is the blast radius — scope it tightly to the one queue,
state machine, or stream.

### Step 4: JWT authorizer (OpenID Connect / Cognito)

HTTP API exposes one authorizer type: `JWT`. API Gateway fetches the
JWKS from `<issuer>/.well-known/openid-configuration` automatically.

```bash
aws apigatewayv2 create-authorizer --api-id <id> \
  --name oidc-auth --authorizer-type JWT \
  --identity-source '$request.header.Authorization' \
  --jwt-configuration audience=<client-id>,issuer=https://<issuer-domain>/
```

**For Cognito user pools**, the issuer is
`https://cognito-idp.<region>.amazonaws.com/<user-pool-id>/` (trailing
slash required) and the audience is the **app client id**.

**Critical JWT config rules:**
- The issuer URL MUST be HTTPS and end with a trailing slash for
  Cognito pools. A missing slash is the #1 cause of "invalid JWT
  configuration" errors.
- Audience must match the `aud` claim in the token. Cognito tokens use
  `client_id` instead of `aud` — API Gateway handles this automatically
  when it detects a Cognito issuer, but for third-party OIDC ensure the
  audience matches.
- `identity-source` defaults to `$request.header.Authorization`. A
  missing or malformed Authorization header returns `401 Unauthorized`
  without invoking the integration.
- Authorizer caching TTL defaults to 0 (no cache). For high-volume
  APIs, set TTL via `authorizerResultTtlInSeconds` on
  `update-authorizer` (300s typical).

```bash
aws apigatewayv2 update-route --api-id <id> --route-id <rid> \
  --authorizer-id <authorizer-id> --authorization-type JWT
```

`AWS_IAM` is set per-route with `--authorization-type AWS_IAM` (no
authorizer ID needed). There is **no Lambda authorizer** on HTTP API;
if you need one, use REST API instead.

### Step 5: CORS configuration

CORS is set at the API level. API Gateway synthesizes `OPTIONS`
preflight responses for any route whose `Access-Control-Allow-Origin`
matches the request origin.

```bash
aws apigatewayv2 update-api --api-id <id> \
  --cors-configuration allowOrigins=https://app.example.com,https://admin.example.com,allowMethods=GET,POST,PUT,DELETE,OPTIONS,allowHeaders=Authorization,Content-Type,X-Request-Id,exposeHeaders=X-Request-Id,X-Trace-Id,maxAge=600,allowCredentials=true
```

**Critical CORS rules:**
- `allowCredentials=true` forbids `allowOrigins=*`. List origins
  explicitly when cookies or Authorization headers cross domains.
- `OPTIONS` MUST be in `allowMethods`, or preflight responses are
  incomplete and browsers block the call.
- `Authorization` MUST be in `allowHeaders` if the API uses a JWT
  authorizer — otherwise the browser cannot send the Bearer token.
- CORS does NOT authorize server-side; it tells the browser whether to
  expose the response to JavaScript. JWT still governs access.

### Step 6: Stage and auto-deploy

`$default` stage is created automatically with `auto-deploy: true`.

```bash
aws apigatewayv2 update-stage --api-id <id> --stage-name '$default' --auto-deploy true

# Named stage:
aws apigatewayv2 create-stage --api-id <id> --stage-name prod --auto-deploy true

# Pinned (release-gated) stage:
aws apigatewayv2 create-deployment --api-id <id>
aws apigatewayv2 update-stage --api-id <id> --stage-name prod \
  --auto-deploy false --deployment-id <deployment-id>
```

**Never** set `auto-deploy: false` without a current `deployment-id` —
the stage serves 404 until a deployment is pinned.

### Step 7: Access logging (JSON)

```bash
aws apigatewayv2 update-stage --api-id <id> --stage-name '$default' \
  --access-log-settings DestinationArn=arn:aws:logs:<region>:<account>:log-group:prod-http-api-access,Format='{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","routeKey":"$context.routeKey","status":"$context.status","responseLength":"$context.responseLength","latency":$context.integrationLatency,"errorMessage":"$context.error.message"}'
```

CloudWatch Logs Insights query:
```
fields @timestamp, status, latency, ip
| filter status >= 400
| stats count() by status
```

### Step 8: Custom domain (API mapping)

```bash
aws apigatewayv2 create-domain-name --domain-name api.example.com \
  --domain-name-configurations certificateArn=arn:aws:acm:<region>:<account>:certificate/<id>,securityPolicy=TLS_1_2

aws apigatewayv2 create-api-mapping --domain-name api.example.com \
  --api-id <api-id> --stage '$default' --api-mapping-key ''
```

- Empty `api-mapping-key` maps the apex of the domain to the stage.
- Non-empty key (e.g., `v1`) maps `api.example.com/v1` to the stage.
- HTTP API does NOT support EDGE custom domains; the cert must be in
  the API's region (`REGIONAL`).

### Step 9: WAFv2 Web ACL

```bash
aws apigatewayv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:<region>:<account>:regional/webacl/prod-http-waf/<id> \
  --resource-arn arn:aws:apigateway:<region>::/apis/<api-id>/stages/$default
```

WAF scope is **REGIONAL** for HTTP API (EDGE not supported).
Recommended managed rules: `AWSManagedRulesCommonRuleSet`,
`AWSManagedRulesKnownBadInputsRuleSet`, and a rate-based rule (e.g.,
2000 requests per 5 minutes per IP).

### Step 10: Throttle and quotas

HTTP API does not have usage plans or API keys. Throttle is set at the
API and route level:

```bash
aws apigatewayv2 update-route --api-id <id> --route-id <rid> \
  --route-settings throttlingRateLimit=100,throttlingBurstLimit=200

aws apigatewayv2 update-stage --api-id <id> --stage-name '$default' \
  --default-route-settings throttlingRateLimit=1000,throttlingBurstLimit=500
```

For per-consumer quotas, use **WAF rate-based rules** keyed on API key
header or JWT claim — there is no native usage plan on HTTP API. If you
need true per-consumer throttling, switch to REST API.

## Expert heuristic: $default stage race with Infrastructure-as-Code

When deploying HTTP API via CloudFormation, CDK, SAM, or Terraform, a
common failure is the `$default` auto-deploy racing the IaC engine's
`AWS::ApiGatewayV2::Deployment` resource. The symptom is drift: the
deployment resource reports CREATE_COMPLETE, but `$default` already
served traffic using the live config seconds earlier.

**Resolution heuristics:**
- Use **one** of: `AWS::ApiGatewayV2::Deployment` + pinned stage, OR
  `auto-deploy: true` with no deployment resource. Mixing both causes
  drift.
- For event-driven pipelines (CodePipeline Source + Build + Deploy),
  set stage `auto-deploy: true` and let CloudFormation manage only
  `::Route`, `::Integration`, `::Authorizer` — skip `::Deployment`.
- For audit-controlled environments, pin the stage and emit
  `::Deployment` with explicit `DependsOn` on every route and
  integration.

A baseline model trained on REST API assumes `create-deployment` is
mandatory. On HTTP API it is **optional and frequently harmful** when
`auto-deploy` is also enabled.

## Expert heuristic: greedy {proxy+} route precedence and the ANY trap

HTTP API route matching uses **most-specific match**, but `ANY` matches
every method including `OPTIONS`. Combined with `{proxy+}` it becomes a
catch-all that defeats narrower routes.

```text
GET /users/me                → exact match, wins over ANY /{proxy+}
ANY /{proxy+}                → catches everything else, ALL methods
ANY /users/{proxy+}          → narrower greedy under /users
$default                     → only when no route matches at all
```

**The ANY trap:** an `ANY /{proxy+}` route with `authorizationType:
NONE` exposes every sub-path on every method (GET, POST, PUT, PATCH,
DELETE, HEAD, OPTIONS). Operators add it for "a single Lambda handles
everything" and forget it includes DELETE. Always bind a JWT authorizer
to ANY routes, or split the greedy into explicit verbs. A baseline
model often suggests `ANY /{proxy+}` as the default route because it
minimizes route count. The secure pattern is the opposite: explicit
verbs, explicit authorizer per route.

## Output format (per HTTP API deployment plan)

```text
API_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Type: HTTP (v2)
  Endpoint: REGIONAL (<region>)
  Routes:
    - GET /health [NONE]
    - GET /users [JWT]
    - POST /users [JWT]
    - GET /users/{userId} [JWT]
    - ANY /{proxy+} [JWT]
  Integrations:
    - Lambda proxy: users-handler
    - Step Functions START_SYNC_EXECUTION: orders-workflow
  Authorization: JWT (issuer https://cognito-idp.<region>.amazonaws.com/<pool>/, audience <client-id>)
  CORS: allowOrigins=https://app.example.com, allowCredentials=true
  Stage: '$default' (auto-deploy=true)
  WAF: <associated ARN> | none
  Custom domain: api.example.com (ACM cert ARN, API mapping key '')
  Logging: CloudWatch JSON access logs to <log-group>
CHECKLIST:
  [x] HTTP API feature fit confirmed (no usage plans / mapping templates / EDGE)
  [x] Routes defined (method + path, ANY / {proxy+} flagged)
  [x] Integrations configured (AWS_PROXY / HTTP_PROXY / STEP_FUNCTION / SQS / KINESIS)
  [x] JWT authorizer with HTTPS issuer + audience verified
  [x] CORS with allowOrigins + Authorization header + OPTIONS
  [x] Stage auto-deploy explicitly set (true | false + deployment-id)
  [x] Access logging to CloudWatch (JSON with $context)
  [x] WAFv2 REGIONAL Web ACL associated with stage
  [x] Custom domain via ACM + API mapping (REGIONAL only)
  [x] Throttle set per route (rate + burst) or via WAF
FINDINGS:
  - [INFO] Estimated cost: $1.00/M requests + data transfer
  - [WARN] No native usage plans — per-consumer throttling via WAF or external
DEPLOY_COMMANDS:
  <ordered list of aws apigatewayv2 commands>
```

## Verification commands (run after deployment)

```bash
aws apigatewayv2 get-api --api-id <id>
aws apigatewayv2 get-routes --api-id <id> --query 'Items[*].[RouteKey,AuthorizationType,Target]'
aws apigatewayv2 get-integrations --api-id <id> --query 'Items[*].[IntegrationType,IntegrationMethod,IntegrationUri]'
aws apigatewayv2 get-authorizer --api-id <id> --authorizer-id <auth-id>
aws apigatewayv2 get-api --api-id <id> --query 'CorsConfiguration'
aws apigatewayv2 get-stage --api-id <id> --stage-name '$default'
aws apigatewayv2 get-web-acl-for-resource --resource-arn arn:aws:apigateway:<region>::/apis/<id>/stages/$default
aws apigatewayv2 get-api-mappings --domain-name api.example.com

# Live invocation
curl -X GET https://<api-id>.execute-api.<region>.amazonaws.com/health
curl -X GET https://<api-id>.execute-api.<region>.amazonaws.com/users -H "Authorization: Bearer <jwt>"
```

## Edge-case handling

- **$default stage 404 after pinning.** A pinned stage
  (`auto-deploy=false`) without a current deployment ID serves 404 for
  every route. Always emit `create-deployment` before pinning.

- **JWT issuer trailing slash.** Cognito issuer URLs MUST end with `/`.
  A missing slash returns "invalid JWT configuration". Third-party OIDC
  providers may or may not require the trailing slash — match the
  OpenID configuration's `issuer` field exactly.

- **Audience mismatch on third-party OIDC.** Cognito uses `client_id`,
  which API Gateway recognizes. Other OIDC providers (Auth0, Okta) emit
  `aud` — the audience list MUST contain the exact `aud` value.

- **CORS `allowCredentials=true` with wildcard origin.** Hard AWS
  rejection — `allowOrigins` must enumerate explicit origins.

- **VPC link to ALB.** ALB is not a valid VPC link target. Front the
  ALB with an NLB, or use HTTP integration with the ALB DNS (which
  exposes the ALB to internet egress).

- **Direct SQS / Kinesis integration role.** The `credentials-arn` role
  must trust `apigateway.amazonaws.com` and have a policy scoped to the
  exact queue or stream ARN. A wildcard (`sqs:*`) creates a privilege
  escalation path if the API is exposed publicly.

## NEVER do these things

1. **NEVER use `ANY /{proxy+}` with `authorizationType: NONE`.** `ANY`
   matches every method (GET, POST, PUT, PATCH, DELETE) on every
   sub-path. Combined with `{proxy+}` (greedy) and no authorizer, this
   exposes every backend operation without authentication. Always bind
   a JWT or AWS_IAM authorizer to catch-all routes, or split the greedy
   into explicit verbs.

2. **NEVER use HTTP API when you need usage plans, API keys, mapping
   templates, resource policies, EDGE endpoints, or Lambda authorizers.**
   HTTP API lacks all of these features. Switch to REST API (v1) and
   use the `apigateway-rest-deployer` skill. The cost of re-platforming
   to REST is far smaller than building workarounds.

3. **NEVER set `auto-deploy: false` without a current `deployment-id`.**
   A pinned stage without a deployment serves 404 for every route.
   Always emit `create-deployment` immediately before pinning.

4. **NEVER trust `allowOrigins=*` with `allowCredentials=true`.** This
   is a hard AWS rejection. With credentials (cookies, Authorization
   header), you MUST enumerate explicit origins. The combination of
   wildcard + credentials is also a browser-level CORS violation that
   browsers block independently.

5. **NEVER create a JWT authorizer with a non-HTTPS issuer or a missing
   trailing slash on Cognito.** The issuer MUST be HTTPS (HTTP issuers
   are rejected). For Cognito user pools, the URL MUST end with a
   trailing slash (`https://cognito-idp.<region>.amazonaws.com/<pool>/`).
   A missing slash is the #1 cause of authorizer creation failure.

Additional hard constraints: never scope the `credentials-arn` IAM role
for direct SQS / Kinesis / Step Functions integrations with wildcards
(privilege escalation path); never use EDGE custom domains on HTTP API
(REGIONAL only — request ACM cert in API region); never mix
`AWS::ApiGatewayV2::Deployment` with `auto-deploy: true` (races and
produces drift); never add explicit `OPTIONS` routes when CORS is
enabled (API Gateway synthesizes preflight); never skip
`lambda:AddPermission` for the `apigateway.amazonaws.com` principal.

## Pre-flight safety checks (run before any deployment CLI)

- **MANDATORY CONFIRMATION GATE.** Before changes go live (auto-deploy
  is on by default!), the deployer MUST emit:
  `CONFIRM: HTTP API <name> has auto-deploy enabled on stage '$default'.
  Any route / integration / authorizer change goes live within seconds.
  Proceed? (yes/no)`
- **Authorizer verification.** List every route; verify `NONE` auth
  appears ONLY on intentionally public routes (e.g., `/health`). The
  catch-all `ANY /{proxy+}` MUST have an authorizer bound.
- **JWT issuer reachability.** Verify
  `<issuer>/.well-known/openid-configuration` returns 200 with a JWKS
  URI. A non-reachable issuer breaks every authorized route.
- **CORS verification.** `allowOrigins` explicit (no `*` with
  credentials), `Authorization` in `allowHeaders` for JWT routes,
  `OPTIONS` in `allowMethods`.
- **Custom domain ACM cert.** Must be in the API's region (REGIONAL).
  HTTP API does not support EDGE custom domains.
- **Cost estimate.** HTTP API $1.00/M requests; WAF $5/ACL/month +
  $0.60/M requests; Cognito $0.0055/MAU; Lambda $0.20/M invocations +
  GB-second; Step Functions Express $1.00/M invocations + GB-second.

## Remediation guidance

**Ordering principle:** authorization first (active exposure if wrong),
then routes and greedy catch-alls (exposure surface), then CORS
(browser UX), then observability (logging), then optimization (WAF,
custom domain, throttle).

- **JWT issuer unreachable or malformed:** resolve the issuer URL via
  `curl <issuer>/.well-known/openid-configuration`; if Cognito, ensure
  trailing slash; verify audience matches the app client id (Cognito)
  or the `aud` claim (third-party OIDC); re-issue `create-authorizer`.
- **VPC link to ALB:** create an NLB that targets the ALB (or the
  ALB's targets directly); verify target groups span multiple AZs;
  create the VPC link; update the HTTP_PROXY integration with
  `connection-type: VPC_LINK` and `connection-id`.
- **HTTP API chosen but REST features required:** confirm whether usage
  plans, mapping templates, resource policies, EDGE, or Lambda
  authorizers are genuinely required. If yes, switch to REST API (no
  in-place conversion — re-create the API). If no, proceed with HTTP
  API and document the trade-off (e.g., per-consumer throttling via
  WAF instead of usage plans).

## Domain

AWS CloudOps / API Gateway HTTP API (v2) Provisioning.

## Recent AWS features (2024-2026)

- **Step Functions direct integration (HTTP API):** HTTP APIs now
  integrate natively with Step Functions (`START_EXECUTION` for
  Standard, `START_SYNC_EXECUTION` for Express) without a Lambda in
  the path. Useful for synchronous workflow APIs (5s ceiling).

- **HTTP API private integrations via VPC Lattice:** HTTP APIs can
  route to VPC Lattice services as private integrations, expanding
  beyond NLB VPC link targets. Lattice auth policies may not appear in
  standard VPC security group audits — check separately.

- **Private integrations with VPC link improvements:** VPC link
  creation supports multiple security groups and subnet IDs directly
  via `create-vpc-link`, removing the need for a separate
  NLB-per-AZ configuration in many cases.

- **HTTP API mTLS:** HTTP APIs support mutual TLS via custom domain
  names. Use for B2B APIs with strict client certificate requirements.

- **OpenAPI 3.1 import + auto-deploy metrics + CORS subdomain
  wildcards:** OpenAPI 3.1 import now carries JWT authorizer and
  direct-integration subtypes; CloudWatch exposes
  `AutoDeployStageChanges` for drift detection; `cors-configuration`
  accepts up to 100 origins and `https://*.example.com` subdomain
  wildcards for tenant apps.

## AWS documentation

- **HTTP API Developer Guide** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api.html
- **API Reference (v2)** — https://docs.aws.amazon.com/apigatewayv2/latest/api-reference/
- **Routes / Integrations / JWT / CORS / Stages (auto-deploy)** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-routes.html
- **Step Functions + API Gateway direct integration** — https://docs.aws.amazon.com/step-functions/latest/dg/connect-api-gateway.html
- **WAFv2 Developer Guide** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html
- **Choosing between REST and HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html
- **Blog: HTTP API mTLS** — https://aws.amazon.com/blogs/compute/introducing-mutual-tls-authentication-for-amazon-api-gateway-http-apis/
