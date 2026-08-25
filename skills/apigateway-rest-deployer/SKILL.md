---
name: apigateway-rest-deployer
description: Provisions production-grade API Gateway REST APIs with correct resource/method models, AWS_PROXY Lambda integrations, IAM/Cognito/Lambda authorizers, stage-level throttling (rate + burst), usage plans with API keys for per-consumer rate limiting, WAFv2 Web ACL association, VPC Link for NLB-backed private integrations, Velocity mapping templates, canary deployments with percentage-based traffic shifting, CloudWatch access logging in JSON, custom domain names via ACM with base path mapping, and REST vs HTTP API (v2) trade-offs. Emits a deployment plan with a READY_TO_DEPLOY checklist. Use when provisioning a new REST API, configuring Lambda proxy with authorizers, setting up usage plans for per-consumer quotas, deploying private integrations via VPC Link, or choosing between REST and HTTP API.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline architecture planning. Live deployment uses aws apigateway create-rest-api, create-resource, put-method, put-integration, create-authorizer, create-usage-plan, create-api-key, create-vpc-link, create-deployment, create-stage, update-stage, aws apigatewayv2 create-api / create-domain-name, and aws wafv2 associate-web-acl (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: experimental
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning a new API Gateway REST API for production, configuring Lambda proxy (AWS_PROXY) integrations with IAM/Cognito/Lambda authorizers, setting up usage plans with API keys for per-consumer rate limiting and quotas, deploying private integrations via VPC Link to an NLB, configuring canary deployments with traffic shifting, enabling access logging to CloudWatch, mapping a custom domain name via ACM, or choosing between REST API (v1) and HTTP API (v2).
  activation_triggers: create a REST API, provision API Gateway, Lambda proxy integration, API Gateway Cognito authorizer, API Gateway usage plan, API Gateway rate limiting, API Gateway VPC Link, canary deployment API Gateway, API Gateway custom domain, REST API vs HTTP API, API Gateway WAF, API Gateway access logging
  invocation_schema: 'Input shape (one of): (a) a deployment specification including API type (REST vs HTTP), endpoint type (EDGE/REGIONAL/PRIVATE), resource and method layout, integration type (AWS_PROXY/AWS/HTTP/MOCK), authorization model, throttling/usage plan requirements, WAF requirements, VPC Link requirements, custom domain requirements, and logging requirements; (b) a partial spec for interactive refinement; (c) an existing REST API ID for architecture review against the well-architected checklist. Output shape: { API_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING, ERROR }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: API Gateway, REST API, HTTP API, API Gateway v2, resource method, AWS_PROXY, Lambda proxy, AWS integration, HTTP integration, MOCK integration, IAM authorization, COGNITO_USER_POOLS, Lambda authorizer, request authorizer, token authorizer, usage plan, API key, throttle, rate limit, burst limit, WAFv2, Web ACL, mapping template, Velocity template, VPC Link, NLB integration, private integration, stage variables, deployment, canary deployment, access logging, custom domain, base path mapping, REST vs HTTP API
  tags: apigateway, app-integration, deploy, rest-api, lambda-proxy, authorizer, usage-plan, throttling, vpc-link, canary, access-logging, custom-domain, waf
---

# API Gateway REST Deployer
Mindset — layered security and contract model (snapshot deployments, API keys are not authentication, REST vs HTTP are different products): [references/advanced-patterns.md](references/advanced-patterns.md).

## Quick reference — deployment checklist

| Dimension | Requirement | Step |
|---|---|---|
| API type | REST (v1) or HTTP (v2) based on feature requirements | Step 1 |
| Endpoint type | EDGE / REGIONAL / PRIVATE (REST); REGIONAL (HTTP) | Step 2 |
| Resource/method | Path segments as resources, verbs as methods per resource | Step 3 |
| Integration | AWS_PROXY (Lambda proxy), AWS (direct), HTTP, HTTP_PROXY, MOCK | Step 4 |
| Authorization | AWS_IAM, COGNITO_USER_POOLS, CUSTOM (Lambda), NONE (rare) | Step 5 |
| Usage plan + API keys | Per-consumer throttling (rate + burst) + quotas | Step 6 |
| Stage throttling | Account/stage-level rate + burst defaults | Step 7 |
| WAFv2 Web ACL | Associated with stage (REGIONAL scope for REST API) | Step 8 |
| VPC Link | For NLB-backed private integrations | Step 9 |
| Mapping templates | Velocity templates for request/response transform | Step 10 |
| Canary deployment | Percentage-based traffic shifting for safe releases | Step 11 |
| Access logging | JSON format with context variables to CloudWatch | Step 12 |
| Custom domain | ACM cert + base path mapping | Step 13 |
| Stage variables | Per-stage config (function ARN, endpoint URL) | Step 14 |

## Pre-flight: deployment specification gate (run before architecture output)

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment** — proceeding with an invalid
spec produces a non-functional or insecure API.

Live-account pre-flight checks (IAM permissions, Lambda function and invoke permission, NLB multi-AZ, Cognito user pool, ACM cert region): [references/diagnostic-commands.md](references/diagnostic-commands.md).

| Attribute | Value | Effect on plan |
|---|---|---|
| `protocolType` | `REST` (v1) | Full feature set. Use for usage plans, mapping templates, resource policies, EDGE. |
| `protocolType` | `HTTP` (v2) | Simpler, cheaper. JWT or IAM auth only. No mapping templates. REGIONAL only. |
| `endpointType` | `EDGE` | Routes through CloudFront. Source IP visible to backend is CloudFront. ACM cert must be us-east-1. |
| `endpointType` | `REGIONAL` | Public regional endpoint. ACM cert in API region. Default for HTTP API. |
| `endpointType` | `PRIVATE` | Only reachable via interface VPC endpoint. Use VPC endpoint policy for access. |
| Authorization | `AWS_IAM` | Sigv4-signed requests. Good for service-to-service. |
| Authorization | `COGNITO_USER_POOLS` | JWT from Cognito. Good for user-facing apps. |
| Authorization | `CUSTOM` (Lambda) | Flexible — request or token authorizer. |
| Authorization | `NONE` | Public. Acceptable ONLY for health checks or public endpoints. |

**If the deployment spec is incomplete** (missing API type, integration,
or authorization model), output:

```text
API_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce a deployment plan without <field> — the resulting API
would be non-functional or insecure.
REQUIRED:
  - api_type (REST or HTTP)
  - endpoint_type (EDGE / REGIONAL / PRIVATE)
  - integration_type (AWS_PROXY / AWS / HTTP / HTTP_PROXY / MOCK)
  - authorization (AWS_IAM / COGNITO_USER_POOLS / CUSTOM / NONE)
  - resource_method_layout (paths and verbs)
```

## Process — Architecture planning (apply in order, produce deployment plan)

### Step 0: Expert knowledge — non-obvious API Gateway behaviors that change the plan
Step 0 expert knowledge — non-obvious behaviors that change the plan (changes not live until create-deployment, API keys are not authentication, ANY/{proxy+} dangers, dormant usage plans, shared account throttle, EDGE client IP, WAF per-IP rules, VTL mapping templates, NLB-only VPC Link, stage variables, canary traffic shifting, JSON access logging, custom domains): [references/advanced-patterns.md](references/advanced-patterns.md).

### Step 1: API type selection — REST (v1) vs HTTP (v2)
Step 1 decision detail — REST (v1) vs HTTP (v2) comparison matrix, decision rule, and migration notes: [references/rest-vs-http-api-guide.md](references/rest-vs-http-api-guide.md).

### Step 2: Endpoint type

| Type | Reachability | Use case |
|---|---|---|
| `EDGE` | Global via CloudFront | API consumed from multiple regions, low latency worldwide. ACM cert must be in us-east-1. |
| `REGIONAL` | Public regional endpoint | Default. API consumed from same region. ACM cert in API region. |
| `PRIVATE` | Only via interface VPC endpoint | Internal APIs. Access controlled by VPC endpoint policy. |

HTTP API supports only `REGIONAL`.

### Step 3: Resource and method model

**REST API resources are path segments.** Each resource has child
resources and methods. The root resource (`/`) has methods like ANY.

```text
/ (root)
├── /users
│   ├── GET (list users)
│   ├── POST (create user)
│   └── /{userId}
│       ├── GET (get user)
│       ├── PUT (update user)
│       └── DELETE (delete user)
└── /orders
    └── ANY (proxy to Lambda for all verbs)
```

**Method configuration:**
```bash
aws apigateway put-method --rest-api-id <id> --resource-id <rid> \
  --http-method GET \
  --authorization-type COGNITO_USER_POOLS \
  --authorizer-id <authorizer-id> \
  --api-key-required false
```

### Step 4: Integration type

| Type | When to use |
|---|---|
| `AWS_PROXY` (Lambda proxy) | Default for Lambda. Passes full request as JSON event to Lambda. Lambda returns status + headers + body. No mapping template needed. |
| `AWS` | Direct AWS service call (e.g., DynamoDB, SNS, SQS). Requires mapping templates for request/response format. |
| `HTTP` | External HTTP endpoint. Requires mapping templates if transform needed. |
| `HTTP_PROXY` | External HTTP endpoint, no transform. Pass-through. |
| `MOCK` | For testing. Returns a fixed response without calling a backend. |

**Lambda proxy (AWS_PROXY):**
```bash
aws apigateway put-integration --rest-api-id <id> --resource-id <rid> \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri arn:aws:apigateway:<region>:lambda:path/2015-03-31/functions/arn:aws:lambda:<region>:<account>:function:<name>/invocations
```

**Lambda permission for API Gateway:**
```bash
aws lambda add-permission --function-name <name> \
  --statement-id apigw-invoke --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn arn:aws:execute-api:<region>:<account>:<api-id>/*/POST/users
```

### Step 5: Authorization
Step 5 detail — authorization model matrix plus Cognito and Lambda request authorizer creation commands: [references/rest-vs-http-api-guide.md](references/rest-vs-http-api-guide.md).

### Step 6: Usage plans and API keys
Step 6 CLI sequences (create-usage-plan with throttle/quota, create-api-key, create-usage-plan-key, per-method apiKeyRequired): [references/usage-plans-vpclink-canary-guide.md](references/usage-plans-vpclink-canary-guide.md).

### Step 7: Stage throttling
Step 7 CLI sequence (update-stage throttle patch-operations; method-level overrides win; burst must be <= 25% of rate): [references/usage-plans-vpclink-canary-guide.md](references/usage-plans-vpclink-canary-guide.md).

### Step 8: WAFv2 Web ACL association

```bash
aws wafv2 create-web-acl --name prod-api-waf --scope REGIONAL \
  --region <api-region> \
  --default-action Allow={} \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=prod-api-waf \
  --rules file://waf-rules.json

aws apigatewayv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:<region>:<account>:regional/webacl/prod-api-waf/<id> \
  --resource-arn arn:aws:apigateway:<region>::/restapis/<api-id>/stages/prod
```

For HTTP API (v2), use the same association — the resource ARN is
`/apis/<api-id>/stages/<stage>`.

**Recommended rule groups:** `AWSManagedRulesCommonRuleSet`,
`AWSManagedRulesSQLiRuleSet`, `AWSManagedRulesKnownBadInputsRuleSet`,
and a rate-based rule (e.g., 2000 requests per 5 minutes per IP).

### Step 9: VPC Link for private integrations
Step 9 CLI sequence (create-vpc-link targeting an NLB, wait for AVAILABLE, connectionType VPC_LINK; NEVER target an ALB directly): [references/usage-plans-vpclink-canary-guide.md](references/usage-plans-vpclink-canary-guide.md).

### Step 10: Mapping templates (REST API only)

Velocity templates transform request/response payloads. HTTP API does
NOT support mapping templates.

**Request mapping (client → integration):**
```velocity
#set($inputRoot = $input.path('$'))
{
  "userId": "$inputRoot.userId",
  "timestamp": "$context.requestTimeEpoch",
  "sourceIp": "$context.identity.sourceIp"
}
```

**Response mapping (integration → client):**
```velocity
#set($inputRoot = $input.path('$'))
{
  "status": 200,
  "data": $inputRoot.items
}
```

**Common `$context` variables:**
`$context.requestId`, `$context.stage`, `$context.httpMethod`,
`$context.resourcePath`, `$context.sourceIp`, `$context.identity.userAgent`,
`$context.responseLatency`, `$context.status`, `$context.error_message`.

### Step 11: Canary deployments
Step 11 CLI sequence (canary percentTraffic / deploymentId / useStageCache; promote at 100%): [references/usage-plans-vpclink-canary-guide.md](references/usage-plans-vpclink-canary-guide.md).

### Step 12: Access logging

```bash
aws apigateway update-stage --rest-api-id <id> --stage-name prod \
  --patch-operations \
    op=replace,path=/accessLogSettings/destinationArn,value=arn:aws:logs:<region>:<account>:log-group:prod-api-access \
    op=replace,path=/accessLogSettings/format,value='{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","caller":"$context.identity.caller","user":"$context.identity.user","requestTime":"$context.requestTime","httpMethod":"$context.httpMethod","resourcePath":"$context.resourcePath","status":"$context.status","protocol":"$context.protocol","responseLength":"$context.responseLength","latency":$context.responseLatency,"errorMessage":"$context.error.message"}'
```

JSON format enables CloudWatch Logs Insights queries:
```
fields @timestamp, status, latency, ip
| filter status >= 400
| stats count() by status
```

### Step 13: Custom domain names

**REST API:**
```bash
aws apigateway create-domain-name \
  --domain-name api.example.com \
  --regional-certificate-arn arn:aws:acm:<region>:<account>:certificate/<id> \
  --endpoint-configuration types=REGIONAL

aws apigateway create-base-path-mapping \
  --domain-name api.example.com \
  --rest-api-id <api-id> \
  --stage prod \
  --base-path v1
```

**HTTP API (v2):**
```bash
aws apigatewayv2 create-domain-name \
  --domain-name api.example.com \
  --domain-name-configurations certificateArn=arn:aws:acm:<region>:<account>:certificate/<id>,endpointType=REGIONAL

aws apigatewayv2 create-api-mapping \
  --domain-name api.example.com \
  --api-id <api-id> \
  --stage prod \
  --api-mapping-key v1
```

**ACM cert:** REGIONAL API = cert in API region. EDGE API = cert in
us-east-1. HTTP API = cert in API region.

### Step 14: Stage variables

Stage variables enable per-stage config. Reference in Lambda integration
URI as `arn:aws:lambda:<region>:<account>:function:${stageVariables.functionName}`.
Set variables via:
```bash
aws apigateway update-stage --rest-api-id <id> --stage-name prod \
  --patch-operations op=replace,path=/variables/functionName,value=prod-handler
```

## Output format (per API deployment plan)

```text
API_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Type: REST (v1) | HTTP (v2)
  Endpoint: EDGE | REGIONAL | PRIVATE
  Resources:
    - /users [GET, POST]
    - /users/{userId} [GET, PUT, DELETE]
  Integration: AWS_PROXY (Lambda proxy) | AWS (direct) | HTTP_PROXY | VPC_LINK
  Authorization: AWS_IAM | COGNITO_USER_POOLS | CUSTOM (Lambda) | NONE
  Usage plan: name, rate=100, burst=200, quota=1M/month
  WAF: <associated ARN> | none
  Custom domain: api.example.com (ACM cert ARN, base path v1)
  Logging: CloudWatch JSON access logs to <log-group>
  Canary: enabled at 10% | disabled
CHECKLIST:
  [x] API type selected based on feature requirements
  [x] Endpoint type matches reachability requirements
  [x] Resources and methods defined
  [x] Integration type configured (AWS_PROXY / AWS / HTTP_PROXY / VPC_LINK)
  [x] Authorization type set per method (NOT NONE for sensitive)
  [x] Usage plan with API keys for per-consumer throttling
  [x] Stage throttling defaults set (rate + burst)
  [x] WAFv2 Web ACL associated with stage
  [x] VPC Link targets NLB (for private integrations)
  [x] Canary deployment enabled for safe releases
  [x] Access logging to CloudWatch (JSON format with $context)
  [x] Custom domain via ACM + base path mapping
  [x] create-deployment emitted as final step
FINDINGS:
  - [INFO] Estimated cost: $3.50/M requests + $0.09/GB data transfer
  - [WARN] Account-level default throttle (10K rps) is shared across all APIs
DEPLOY_COMMANDS:
  <ordered list of aws apigateway / apigatewayv2 commands>
```

### Worked example — Lambda proxy REST API with Cognito + usage plans + WAF

```text
API_SPEC: prod-user-service-api
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Type: REST (v1)
  Endpoint: REGIONAL (us-east-1)
  Resources:
    - /users [GET (list), POST (create)]
    - /users/{userId} [GET, PUT, DELETE]
  Integration: AWS_PROXY (Lambda: user-service-handler)
  Authorization: COGNITO_USER_POOLS (user pool: prod-users-pool)
  Usage plan: prod-consumer-plan, rate=100, burst=200, quota=1M/month
  WAF: arn:aws:wafv2:us-east-1:111111111111:regional/webacl/prod-api-waf/abc
  Custom domain: api.example.com (ACM cert, base path v1)
  Logging: CloudWatch JSON access logs to /aws/apigateway/prod-user-service
  Canary: enabled at 10% traffic
CHECKLIST:
  [x] Type: REST (v1) — usage plans and mapping templates required
  [x] Endpoint: REGIONAL — consumers in us-east-1
  [x] Resources: /users, /users/{userId} with standard CRUD verbs
  [x] Integration: AWS_PROXY Lambda — no mapping template needed
  [x] Authorization: COGNITO_USER_POOLS — authorizer configured
  [x] Usage plan: prod-consumer-plan linked to prod stage with API key
  [x] Stage throttling: default 1000 rps / 500 burst, per-method overrides
  [x] WAF: REGIONAL Web ACL with CommonRuleSet + rate-based rule
  [x] VPC Link: N/A (Lambda integration)
  [x] Canary: 10% traffic shifting enabled
  [x] Access logging: JSON format with $context.requestId, status, latency
  [x] Custom domain: api.example.com + base path v1 mapping
  [x] create-deployment: emitted as final step
FINDINGS:
  - [INFO] Estimated cost: $3.50/M requests + Lambda cost + $5/WAF/month
  - [INFO] JWT validation offloaded to Cognito authorizer — no Lambda needed
  - [WARN] Account-level default throttle shared across all APIs in us-east-1
DEPLOY_COMMANDS:
  1. aws apigateway create-rest-api --name prod-user-service --endpoint-configuration types=REGIONAL
  2. aws apigateway create-resource (root /users, /{userId})
  3. aws apigateway put-method (GET, POST on /users; GET, PUT, DELETE on /{userId})
  4. aws apigateway create-authorizer --type COGNITO_USER_POOLS --provider-arns <pool-arn>
  5. aws apigateway put-integration --type AWS_PROXY --uri <lambda-arn>
  6. aws lambda add-permission --principal apigateway.amazonaws.com --action lambda:InvokeFunction
  7. aws apigateway create-usage-plan --throttle burstLimit=200,rateLimit=100
  8. aws apigateway create-api-key --enabled
  9. aws apigateway create-usage-plan-key --usage-plan-id <plan> --key-id <key>
  10. aws wafv2 create-web-acl --scope REGIONAL
  11. aws apigateway create-deployment --rest-api-id <id> --stage-name prod
  12. aws apigatewayv2 associate-web-acl (associate WAF with stage ARN)
  13. aws apigateway update-stage (canary 10% + access logging JSON)
  14. aws apigateway create-domain-name + create-base-path-mapping (api.example.com/v1)
```

## Verification commands (run after deployment)
Verification commands (get-stage, get-methods authorization check, usage-plan keys, WAF association, access logging, curl invocation, base-path mappings): [references/diagnostic-commands.md](references/diagnostic-commands.md).

## Edge-case handling
Edge-case handling (undeployed stage, cross-region Lambda, rotating attackers vs WAF, Cognito authorizer caching TTL, EDGE source IP, HTTP API without authorizer): [references/advanced-patterns.md](references/advanced-patterns.md).

## Anti-Patterns — NEVER

- NEVER treat `apiKeyRequired: true` as authentication. API keys are
  usage-plan identifiers, not auth credentials. They are in cleartext
  and extractable from client code. Use AWS_IAM, COGNITO_USER_POOLS, or
  a Lambda authorizer.

- NEVER modify methods/resources without `create-deployment`. The
  deployment is the snapshot that goes live. Operators who change auth
  type without deploying leave the OLD (often insecure) config serving.
  Always emit `create-deployment` as the final command.

- NEVER put an ALB directly behind a VPC Link. Only NLB is supported as
  a VPC Link target. Front the ALB with an NLB, or use HTTP integration
  with the ALB DNS (which exposes the ALB to internet egress).

- NEVER set `authorizationType: NONE` on ANY method for sensitive data.
  ANY covers GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS — including
  destructive verbs. Use an authorizer on the ANY method.

- NEVER rely on the account-level default throttle (10K rps). It is
  shared across all APIs in the region. One abused API can 429 every
  other API. Always create a usage plan with explicit per-consumer
  throttles.

- NEVER create an EDGE API with an ACM cert outside us-east-1. EDGE APIs
  route through CloudFront, which reads ACM only from us-east-1. This is
  an AWS hard constraint.

- NEVER assume a usage plan without API keys provides rate limiting.
  A plan with zero linked keys cannot enforce any throttle or quota.

- NEVER skip access logging for a production API. JSON-format CloudWatch
  access logs are the primary forensic signal for breach investigation,
  latency diagnosis, and compliance audit.

- NEVER use HTTP API when you need usage plans, API keys, mapping
  templates, resource policies, or EDGE endpoints. HTTP API lacks these
  features. Use REST API for these use cases.

- NEVER assume `aws:SourceIp` works on EDGE APIs. The source IP is a
  CloudFront edge IP. Use WAF or Lambda authorizer reading
  `x-forwarded-for` for client-IP restrictions.

- NEVER forget `lambda:AddPermission` for API Gateway to invoke the
  Lambda function. Without it, the integration returns 500 with
  "Invalid permissions on Lambda function."

- NEVER use a Cognito authorizer without verifying the user pool ID and
  app client are correct. A misconfigured authorizer may silently fall
  through to unauthenticated access during deployment windows.

- NEVER skip canary for high-traffic API changes. Direct-to-prod
  deployments risk a bad config affecting 100% of traffic. Use a 5-10%
  canary for at least 30 minutes before promotion.

## Pre-flight safety checks (run before any deployment CLI)

- **MANDATORY CONFIRMATION GATE.** Before `create-deployment` (which
  makes config live), the deployer MUST emit:
  `CONFIRM: About to deploy API <name> stage <stage>. This makes the
  current configuration live to all consumers. Proceed? (yes/no)`

- **Authorization model verification.** Before deployment, list all
  methods and verify NONE auth appears ONLY on intentionally public
  endpoints. A misconfigured authorizer on a sensitive method is the
  most common API Gateway incident.

- **Usage plan + API key verification.** If the spec requires per-consumer
  rate limiting, verify the usage plan exists AND has at least one API
  key linked. A plan without keys is dormant.

- **WAF scope verification.** For REST APIs, WAF must be REGIONAL scope
  in the API's region. For HTTP APIs, same. EDGE APIs use CloudFront
  scope in us-east-1 (via the API Gateway CloudFront distribution).

- **Custom domain ACM cert verification.** The cert must cover the
  domain and be in the correct region (REGIONAL: API region; EDGE:
  us-east-1).

- **Cost estimate.** Emit before deployment:
  - REST API: $3.50/M requests + data transfer
  - HTTP API: $1.00/M requests + data transfer
  - WAF: $5/ACL/month + $0.60/M requests
  - Cognito: $0.0055/MAU (free tier: 50K MAU)
  - Lambda: $0.20/M invocations + GB-second

- **Deployment is irreversible without versioning.** API Gateway does
  not keep deployment history beyond the stages that reference them. Use
  canary for rollback safety. Document the prior deployment ID before
  each `create-deployment`.

## Remediation guidance
Remediation guidance — PREREQUISITES_MISSING fixes (ACM cert region, VPC Link to ALB, cross-region Lambda) under the ordering principle authorization first, then deployment snapshot, then throttling, then optimization: [references/error-handling.md](references/error-handling.md).

## References (load on demand)

- [REST vs HTTP API guide](references/rest-vs-http-api-guide.md) - full REST/HTTP comparison, decision tree, authorization models (Steps 1, 5)
- [Usage plans, VPC Link, and canary guide](references/usage-plans-vpclink-canary-guide.md) - usage plans and API keys, throttle semantics, VPC Link, canary deployments (Steps 6, 7, 9, 11)
- [Diagnostic commands](references/diagnostic-commands.md) - live-account pre-flight checks, post-deployment verification commands
- [Error handling](references/error-handling.md) - PREREQUISITES_MISSING remediations (ACM cert region, ALB VPC Link, cross-region Lambda)
- [Advanced patterns](references/advanced-patterns.md) - mindset, Step-0 expert knowledge, edge-case handling, recent AWS features

## Domain

AWS CloudOps / API Gateway REST & HTTP API Provisioning.

## Recent AWS features (2024-2026)
Recent AWS features 2024-2026 (HTTP API mTLS, VPC Lattice, OpenAPI 3.1, v2 OpenAPI importer, weighted canary logging, WebSocket GA): [references/advanced-patterns.md](references/advanced-patterns.md).

## AWS documentation

- **API Gateway Developer Guide** — https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html
- **API Gateway API Reference (v1)** — https://docs.aws.amazon.com/apigateway/latest/api/
- **API Gateway API Reference (v2)** — https://docs.aws.amazon.com/apigatewayv2/latest/api-reference/
- **API Gateway Security** — https://docs.aws.amazon.com/apigateway/latest/developerguide/security.html
- **API Gateway CLI Reference (v1)** — https://docs.aws.amazon.com/cli/latest/reference/apigateway/
- **API Gateway CLI Reference (v2)** — https://docs.aws.amazon.com/cli/latest/reference/apigatewayv2/
- **Choosing between REST and HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html
- **WAFv2 Developer Guide** — https://docs.aws.amazon.com/waf/latest/developerguide/waf-chapter.html
- **Blog: HTTP API mTLS** — https://aws.amazon.com/blogs/compute/introducing-mutual-tls-authentication-for-amazon-api-gateway-http-apis/
- **Blog: VPC Lattice + API Gateway** — https://aws.amazon.com/blogs/compute/building-secure-internal-apis-with-amazon-api-gateway-and-amazon-vpc-lattice/
