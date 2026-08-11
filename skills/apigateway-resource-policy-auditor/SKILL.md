---
name: apigateway-resource-policy-auditor
description: >-
  Audits AWS API Gateway REST/HTTP APIs for unauthenticated public methods
  (authorizationType NONE), API-key-as-auth misconceptions, cross-account
  resource policy grants, missing usage plans and rate limiting, and absent
  WAF Web ACL associations. Emits a deterministic verdict (PUBLIC_NO_AUTH |
  NO_RATE_LIMIT | CONFIG_GAP | OK) per API with enumerated findings and CLI
  remediation. Use when reviewing API Gateway security posture, checking for
  open methods, validating rate-limiting coverage, auditing resource policies
  for cross-account exposure, or verifying WAF protection before production.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline config classification. Live-account
  audits use aws apigateway get-rest-apis, get-resources, get-method,
  get-stage, get-usage-plans, and aws wafv2 get-web-acl-for-resource
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - API Gateway
  - resource policy
  - authorizationType NONE
  - PUBLIC_NO_AUTH
  - usage plan
  - rate limiting
  - throttle
  - WAF Web ACL
  - cross-account
  - API key
  - execute-api:Invoke
  - REST API
  - HTTP API
  - EDGE endpoint
  - REGIONAL endpoint
  - PRIVATE endpoint
  - COGNITO_USER_POOLS
  - method authorization
  - API security audit
tags: [apigateway, security, resource-policy, authorization, rate-limiting, waf, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  verdict_shape: "PUBLIC_NO_AUTH | NO_RATE_LIMIT | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing an API Gateway REST/HTTP API before production deployment,
    checking for methods with no authentication, validating usage-plan
    coverage and rate limiting, auditing a resource policy for cross-account
    exposure, or verifying WAF Web ACL association.
  activation_triggers:
    - "audit this API Gateway"
    - "is my API publicly accessible"
    - "check API Gateway authorization"
    - "API Gateway no auth methods"
    - "is there a usage plan for my API"
    - "does my API have WAF"
    - "cross-account API Gateway resource policy"
    - "API key required but no auth"
    - "API Gateway rate limiting"
  invocation_schema: >-
    Input: either (a) API Gateway configuration (API metadata + methods +
    stage + resource policy + usage plan + WAF status), OR (b) a REST API
    id for live-account audit. Output: deterministic API/VERDICT/REASON/
    FINDINGS/REMEDIATION block per API, where VERDICT in {PUBLIC_NO_AUTH,
    NO_RATE_LIMIT, CONFIG_GAP, OK, ERROR}.
---

# API Gateway Resource Policy Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across all
dimensions, and `authorizationType: NONE` on a public endpoint is the single
most dangerous API Gateway misconfiguration — it exposes backend logic and
data to the entire internet with zero identity verification.

API Gateway is the front door to backend services. Its security model has
three independent layers that are frequently misunderstood:

1. **Method authorization** (`authorizationType`) — the primary gate.
   `NONE` means the method is callable by anyone who can reach the endpoint.
   `apiKeyRequired` is NOT a substitute — API keys are identification tokens
   for usage plans, not authentication credentials.

2. **Resource policy** — a JSON policy attached to the REST API that can
   restrict which principals may invoke the API. On a method with
   `authorizationType: NONE`, the resource policy is the ONLY access control.
   On a method with `AWS_IAM`, both layers must allow the request.

3. **Usage plan + rate limiting** — per-key throttling and quotas that
   prevent abuse. Without a usage plan, only the account-level default
   throttle applies (10,000 rps / 5,000 burst) — shared across all APIs
   in the account.

A missing WAF Web ACL is the fourth dimension — defense-in-depth against
SQLi, XSS, and rate-based attacks.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Any method `authorizationType: NONE` on EDGE/REGIONAL API | **PUBLIC_NO_AUTH** | Step 2a |
| `authorizationType: NONE` + `apiKeyRequired: true` (API key is NOT auth) | **PUBLIC_NO_AUTH** | Step 2b |
| No usage plan associated with the stage | **NO_RATE_LIMIT** | Step 3 |
| Resource policy `Principal: "*"` on `execute-api:Invoke` + no condition | **CONFIG_GAP** | Step 4a |
| No WAF Web ACL associated with the stage | **CONFIG_GAP** | Step 5 |
| All methods authenticated + usage plan + WAF + scoped resource policy | **OK** | Step 6 |
| `endpointType: PRIVATE` (not publicly reachable) | **OK** on PUBLIC dimension | Step 1 |

See the ordered steps below for edge cases.

## Pre-flight: API type and endpoint classification

Before evaluating security, classify the API type and endpoint. Several
attributes short-circuit the audit.

| Attribute | Value | Effect on audit |
|---|---|---|
| `protocolType` | `REST` | REST API (v1). Supports resource policies, usage plans, API keys, WAF. Full audit applies. |
| `protocolType` | `HTTP` | HTTP API (v2). Does NOT support resource policies or API keys. JWT authorizers or IAM auth only. Skip resource-policy and usage-plan dimensions. |
| `endpointType` | `EDGE` | API is accessible globally via CloudFront. Source IP visible to backend is CloudFront, not client. Fully public. |
| `endpointType` | `REGIONAL` | API is accessible within the region via a public regional endpoint. Fully public. |
| `endpointType` | `PRIVATE` | API is accessible ONLY via interface VPC endpoints. Not publicly reachable. Skip PUBLIC_NO_AUTH check. Still audit method auth and WAF. |

**Multi-API sweep note (pagination):** `aws apigateway get-rest-apis` returns
at most 500 per page. Use `--position` from the prior response to page
through all APIs. For each API, also page `get-resources` (500/page) and
`get-methods` per resource — both silently truncate. Always drain pagination
tokens to completion.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious API Gateway behaviors

These behaviors change classification if ignored:

- **API keys are NOT authentication.** `apiKeyRequired: true` on a method
  with `authorizationType: NONE` provides ZERO access control. The API key
  is a plaintext token in the `x-api-key` header — shareable, guessable,
  and leakable via browser dev tools, client-side code, or git. A method
  relying on API keys for "security" is PUBLIC_NO_AUTH, not OK.

- **HTTP APIs (v2) do NOT support resource policies.** Only REST APIs (v1)
  have a resource policy. Auditing a resource policy on an HTTP API is a
  no-op — skip Step 4 entirely. HTTP APIs use JWT authorizers or IAM auth.

- **`authorizationType` is per-method, not per-API.** Each resource/method
  combination has its own auth setting. A single API can mix authenticated
  and unauthenticated methods. One `NONE` method makes the entire API
  PUBLIC_NO_AUTH — the weakest method determines the API's exposure.

- **The ANY method covers ALL HTTP verbs.** ANY maps to GET, POST, PUT,
  PATCH, DELETE, HEAD, and OPTIONS simultaneously. An ANY method with
  `authorizationType: NONE` exposes every operation on that resource path
  unauthenticated. This is worse than a single-verb NONE because it covers
  destructive operations (DELETE, PUT).

- **Resource policy evaluation differs by auth type.** When
  `authorizationType: AWS_IAM`, both the resource policy AND the caller's
  IAM identity-based policy must allow the request (intersection for
  cross-account, union for same-account). When `authorizationType: NONE`,
  the resource policy is the ONLY gate — if it is empty or allows `"*"`,
  the method is fully open to the internet.

- **EDGE endpoints route through CloudFront.** The client IP is not visible
  to the API or the backend — all requests appear to come from CloudFront
  edge IPs. IP-based conditions in the resource policy
  (`aws:SourceIp`) match CloudFront IPs, not client IPs. To enforce client
  IP restrictions on EDGE APIs, use `x-forwarded-for` via a Lambda
  authorizer or WAF, not the resource policy.

- **Usage plans require API keys to enforce.** A usage plan with zero
  associated API keys provides no per-key throttling — the plan exists but
  cannot enforce limits. Check both the plan AND its linked keys.

- **Account-level default throttle is shared.** Without a usage plan, the
  account-level default (10,000 rps, burst 5,000) is shared across ALL APIs
  in the account in that region. One abused API can exhaust the limit and
  throttle every other API in the account.

- **WAF can only be associated with deployed stages.** A stage that exists
  but has no current deployment cannot have a WAF Web ACL associated.
  Always verify the stage deployment status before reporting a missing WAF.

- **COGNITO_USER_POOLS without a configured authorizer is effectively NONE.**
  A method with `authorizationType: COGNITO_USER_POOLS` but no authorizerId
  configured will reject all requests — but during deployment windows or
  misconfiguration, the method may fall through to unauthenticated access.
  Always verify the authorizer is linked.

- **The `{proxy+}` greedy-path resource catches all sub-paths.** A resource
  path configured as `{proxy+}` acts as a catch-all for any path segment
  beneath it. If the ANY method on `{proxy+}` has `authorizationType: NONE`,
  every sub-path is exposed unauthenticated — not just the root. This is
  the most dangerous resource configuration because it silently exposes
  routes the operator may not realise exist.

- **Auth changes require a deployment to take effect.** Modifying
  `authorizationType` or `apiKeyRequired` via `update-method` does NOT
  change the live API until a new deployment is created
  (`create-deployment`). An operator who changes auth but forgets to
  deploy leaves the OLD (insecure) configuration live. Always verify the
  deployment timestamp after remediation.

- **The 10,000 rps default throttle is per-region, not per-API.** All APIs
  in the account share one regional throttle budget. A single abused
  unauthenticated API can exhaust the budget and cause 429 responses on
  every other API in that region — even APIs in entirely different VPCs
  or business units. This blast-radius amplification is why NO_RATE_LIMIT
  on a PUBLIC_NO_AUTH API is an incident, not a config note.

- **WAF rate-based rules count per client IP, not per API key.** A WAF
  rate-based rule with `AggregateKeyType: IP` limits requests per source
  IP. This does NOT correlate with API keys — one attacker rotating
  across 100 IPs with 100 API keys bypasses a 2,000-req/5-min IP rule.
  For per-key limiting, only usage-plan throttling is effective.

### Step 1: Endpoint type gate (short-circuit for PRIVATE APIs)

If `endpointType` is `PRIVATE`:
- The API is only reachable via interface VPC endpoints — it is NOT on
  the public internet. Skip the PUBLIC_NO_AUTH check (Step 2).
- Still audit: resource policy cross-account exposure (Step 4), usage plan
  (Step 3), WAF (Step 5), and method auth (a PRIVATE API with NONE auth is
  still a risk within the VPC).
- A PRIVATE API with all methods authenticated, a usage plan, and WAF is OK.

If `endpointType` is `EDGE` or `REGIONAL`:
- The API is publicly reachable. Proceed to Step 2 (authorization check).

### Step 2: Method authorization evaluation (PUBLIC_NO_AUTH dimension)

For each method on each resource:

**Step 2a: Check authorizationType.**
- `authorizationType: NONE` on an EDGE/REGIONAL API → **PUBLIC_NO_AUTH**.
  The method is callable by anyone on the internet. This is the worst
  verdict. The resource policy MAY restrict this (see Step 2c), but an
  empty or permissive resource policy means full public exposure.

- `authorizationType: AWS_IAM` → authenticated. The caller must present
  valid AWS credentials. Proceed to resource policy check (Step 4).

- `authorizationType: COGNITO_USER_POOLS` → authenticated. Verify the
  authorizer is configured (authorizerId is set). If no authorizerId,
  flag as CONFIG_GAP (broken auth configuration).

- `authorizationType: CUSTOM` → authenticated. Verify the authorizer
  Lambda function ARN is set. If not, flag as CONFIG_GAP.

**Step 2b: API key is NOT authentication.**
A method with `authorizationType: NONE` + `apiKeyRequired: true` is
still **PUBLIC_NO_AUTH**. The API key gates access to the usage plan
(throttling/quotas) but provides no identity verification. The key is
transmitted in cleartext and can be extracted from client-side code.

**Step 2c: Resource policy restriction on NONE-auth methods.**
If `authorizationType: NONE` but the resource policy contains a Deny
statement restricting access to specific accounts/IPs (e.g.,
`aws:SourceAccount` condition), the method is not fully public. This is
unusual and fragile — downgrade to **CONFIG_GAP** with a finding noting
the reliance on resource policy as the sole access control on a
NONE-auth method.

### Step 3: Usage plan and rate-limiting evaluation

Check whether a usage plan is associated with the API's stage:

- **No usage plan associated** → add **NO_RATE_LIMIT** finding. Without
  a usage plan, there is no per-key throttling or quota enforcement. The
  account-level default throttle (10,000 rps) is the only protection,
  shared across all APIs in the account.

- **Usage plan exists but no API keys associated** → add NO_RATE_LIMIT
  finding. The plan cannot enforce limits without keys.

- **Usage plan with throttle and/or quota + at least one API key** → OK
  for this dimension. The throttle rate, burst, and quota values are
  informational — flag only if the values are implausibly high (e.g.,
  throttle > 10,000 rps, which exceeds the account default and is
  effectively unlimited).

**PRIVATE API exception:** a PRIVATE API may not require a usage plan if
the VPC endpoint policy controls access. Do NOT flag NO_RATE_LIMIT on a
PRIVATE API unless the VPC endpoint policy is permissive (allows all
principals).

### Step 4: Resource policy cross-account evaluation

For REST APIs only (HTTP APIs skip this step):

- **No resource policy** → OK for this dimension (same-account access is
  the default for REST APIs — the API owner's account always has access).

- **Principal `"*"` on `execute-api:Invoke` with no condition** → add
  **CONFIG_GAP** finding. Any AWS account can invoke the API. If methods
  have `AWS_IAM` auth, cross-account callers still need IAM permissions,
  but the resource policy is too broad. If methods have `NONE` auth, the
  finding is already PUBLIC_NO_AUTH (Step 2 supersedes).

- **Cross-account principal (specific external account ARN) with no
  condition** → add CONFIG_GAP finding. Less severe than wildcard but
  still a cross-account exposure surface.

- **Cross-account principal with `aws:SourceAccount` or `aws:SourceArn`
  condition** → OK for this dimension (scoped). Note the dependency on
  the condition remaining correct.

- **Deny statement restricting to same account** → OK (explicit
  restriction is the strongest posture).

### Step 5: WAF Web ACL association evaluation

Check whether a WAF Web ACL is associated with the API stage:

- **No WAF Web ACL associated** → add **CONFIG_GAP** finding. The API
  has no protection against SQLi, XSS, bot traffic, or rate-based
  attacks. WAF is the defense-in-depth layer that catches attacks the
  application layer might miss.

- **WAF Web ACL associated** → OK for this dimension. Note the ACL name
  for reference. Recommend verifying the ACL's rule groups include
  rate-based rules and AWS managed rule groups.

### Step 6: Aggregation — worst verdict wins

The final verdict is the **maximum severity** across all dimensions:

```
verdict = max(auth_finding, usage_plan_finding, resource_policy_finding, waf_finding)
```

Severity order: PUBLIC_NO_AUTH > NO_RATE_LIMIT > CONFIG_GAP > OK.

## Output format (per API)

```text
API: <api-id>
VERDICT: PUBLIC_NO_AUTH | NO_RATE_LIMIT | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [PUBLIC_NO_AUTH] <finding description (Step Na)>
  - [CONFIG_GAP] <finding description (Step Nb)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

**HTTP API (v2) output:** the same format applies, but FINDINGS for
Step 4 (resource policy) are omitted — HTTP APIs do not support resource
policies. If the HTTP API has no JWT or IAM authorizer, the verdict is
PUBLIC_NO_AUTH. Note "HTTP API — resource policy N/A" in FINDINGS.

**Stage not deployed:** if the stage exists but has no current deployment,
output:
```text
API: <api-id>
VERDICT: ERROR
REASON: Stage <stage> has no active deployment — configuration is not live.
REMEDIATION: Deploy the API: aws apigateway create-deployment --rest-api-id <id> --stage-name <stage>.
```

### Worked example — public method with no usage plan and no WAF

```text
API: api-prod-gateway
VERDICT: PUBLIC_NO_AUTH
REASON: Method GET /orders has authorizationType NONE on a REGIONAL endpoint
with no resource-policy restriction — callable by anyone on the internet
(Step 2a). No usage plan or WAF compounds the exposure.
FINDINGS:
  - [PUBLIC_NO_AUTH] GET /orders authorizationType NONE on REGIONAL endpoint (Step 2a)
  - [NO_RATE_LIMIT] No usage plan associated with stage prod (Step 3)
  - [CONFIG_GAP] No WAF Web ACL on stage prod (Step 5)
REMEDIATION:
  1. Set authorizationType to AWS_IAM or COGNITO_USER_POOLS on GET /orders.
  2. Create a usage plan and associate it with stage prod.
  3. Associate a WAF Web ACL with the stage.
```

## Edge-case handling

- **HTTP API (v2) with no JWT authorizer.** An HTTP API without a JWT or
  IAM authorizer is effectively public — no method-level auth and no
  resource policy to fall back on. Classify as PUBLIC_NO_AUTH if the
  routes are publicly reachable.

- **Mixed-auth API.** An API with some methods NONE and others AWS_IAM
  is PUBLIC_NO_AUTH — the weakest method determines exposure. The IAM-
  authenticated methods are not compromised, but the NONE method provides
  a path to the backend.

- **Resource policy with `NotPrincipal`.** A resource policy using
  `NotPrincipal` in an Allow grants access to every principal EXCEPT the
  listed ones — the inverse of the intended scope. Treat as wildcard
  exposure (CONFIG_GAP at minimum).

- **Stage not deployed.** A stage that exists but has no current
  deployment is not serving traffic. Note this in the output: "Stage has
  no active deployment — configuration is not live." Do not emit a
  verdict on an undeployed stage; emit INFO.

- **API with zero resources/methods.** An API with no configured methods
  has no attack surface. Output VERDICT: OK with a note: "No methods
  configured — API has no attack surface."

## Anti-Patterns — NEVER

- NEVER treat `apiKeyRequired: true` as a security control when
  `authorizationType` is NONE. API keys are usage-plan identifiers, not
  authentication credentials. They are transmitted in cleartext in the
  `x-api-key` header and can be extracted from client-side code, browser
  dev tools, or git repositories. A method with NONE auth + API key is
  PUBLIC_NO_AUTH.

- NEVER classify an EDGE or REGIONAL API with `authorizationType: NONE`
  as CONFIG_GAP or OK. A NONE-auth method on a public endpoint is
  callable by anyone on the internet — this is PUBLIC_NO_AUTH, the
  most severe verdict. The presence of a resource policy that restricts
  access is the ONLY exception (Step 2c), and even then the finding is
  CONFIG_GAP (fragile), not OK.

- NEVER audit a resource policy on an HTTP API (v2). HTTP APIs do not
  support resource policies — the policy field is always empty. This is
  not a finding. Skip Step 4 for HTTP APIs and audit JWT authorizers
  instead.

- NEVER assume all methods on an API share the same authorizationType.
  Each method has its own setting. A thorough audit must enumerate every
  resource/method pair. A common misconfiguration is a secure GET method
  alongside an insecure POST or ANY on the same resource.

- NEVER treat `aws:SourceIp` in a resource policy as a reliable access
  control on EDGE APIs. EDGE APIs route through CloudFront — the source
  IP is a CloudFront edge IP, not the client IP. A SourceIp condition
  on an EDGE API restricts nothing meaningful. Only WAF or a Lambda
  authorizer can enforce client-IP restrictions on EDGE APIs.

- NEVER flag a PRIVATE API as PUBLIC_NO_AUTH. PRIVATE endpoints are only
  reachable via interface VPC endpoints — they are not on the public
  internet. A PRIVATE API with NONE-auth methods is a CONFIG_GAP (risk
  within the VPC), not PUBLIC_NO_AUTH.

- NEVER assume a usage plan without API keys provides rate limiting.
  A usage plan with zero associated keys cannot enforce any throttle or
  quota — it is a dormant configuration. Always verify the plan has at
  least one API key linked.

- NEVER ignore the ANY method. ANY covers GET, POST, PUT, PATCH, DELETE,
  HEAD, and OPTIONS simultaneously. An ANY method with NONE auth is
  worse than a single-verb NONE method because it exposes destructive
  operations (DELETE, PUT) without authentication.

- NEVER treat `COGNITO_USER_POOLS` or `CUSTOM` auth as verified if the
  authorizerId is missing. A method configured with COGNITO_USER_POOLS
  but no authorizer is broken — it either rejects all traffic (fail
  closed) or, during misconfiguration windows, falls through to
  unauthenticated. Flag as CONFIG_GAP.

- NEVER recommend deleting an API as remediation. APIs have backend
  integrations, client consumers, and CloudFront distributions that
  depend on them. Remediation is always to fix the authorization,
  not to remove the API.

- NEVER assume the account-level default throttle protects individual
  APIs from abuse. The default (10,000 rps / 5,000 burst) is shared
  across all APIs in the account. One abused API can exhaust the
  budget and throttle every other API.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (update-method, create-usage-plan, associate-web-acl, put-rest-api),
  the auditor MUST emit:
  `CONFIRM: About to <action> on API <id> stage <stage>. This affects
  <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- Verify the API exists and is accessible:
  `aws apigateway get-rest-api --rest-api-id <id> --profile <p>` — fail
  closed if it returns an error.

- Capture the current method configuration before modifying:
  `aws apigateway get-method --rest-api-id <id> --resource-id <rid>
  --http-method <verb> --profile <p>` BEFORE any update-method call.

- Changing `authorizationType` from NONE to AWS_IAM or
  COGNITO_USER_POOLS will break existing unauthenticated callers. Identify
  all consumers (CloudFront distributions, SDK clients, mobile apps)
  before modifying auth. Emit a warning listing the impact.

- Associating a WAF Web ACL requires the Web ACL to exist in the same
  region as the API (for REGIONAL) or us-east-1 (for EDGE/CloudFront).
  Verify the ACL exists before associating.

- Prefer additive changes (add a usage plan, associate WAF) over
  destructive changes (change auth type) — additive changes do not
  break existing consumers. Fix auth type first, then add rate limiting
  and WAF, in that order.

## Remediation guidance

### For PUBLIC_NO_AUTH — method with authorizationType NONE

1. **Immediately** set the method's `authorizationType` to `AWS_IAM`,
   `COGNITO_USER_POOLS`, or a `CUSTOM` Lambda authorizer:
   ```bash
   aws apigateway update-method --rest-api-id <id> \
     --resource-id <rid> --http-method <verb> \
     --patch-operations op=replace,path=/authorizationType,value=AWS_IAM \
     --profile <p>
   aws apigateway create-deployment --rest-api-id <id> --stage-name <stage>
   ```
2. If the method MUST be public (e.g., a health-check endpoint), add a
   resource policy restricting to known IPs/accounts, AND associate a
   WAF Web ACL with rate-based rules.
3. If `apiKeyRequired` was the intended "security" control, replace it
   with a proper authorizer. API keys are not authentication.

### For NO_RATE_LIMIT — no usage plan

1. Create a usage plan with throttle and quota:
   ```bash
   aws apigateway create-usage-plan --name "<api>-plan" \
     --throttle burstLimit=200,rateLimit=100 \
     --quota limit=10000,period=DAY \
     --api-stages apiId=<id>,stage=<stage> \
     --profile <p>
   ```
2. Create an API key and link it to the usage plan:
   ```bash
   aws apigateway create-api-key --name "<api>-key" --enabled
   aws apigateway create-usage-plan-key --usage-plan-id <plan-id> \
     --key-id <key-id> --key-type API_KEY --profile <p>
   ```
3. Require the API key on methods that need per-key throttling:
   ```bash
   aws apigateway update-method --rest-api-id <id> \
     --resource-id <rid> --http-method <verb> \
     --patch-operations op=replace,path=/apiKeyRequired,value=true
   ```

### For CONFIG_GAP — cross-account resource policy

1. Replace `Principal: "*"` with specific account/role ARNs:
   ```bash
   aws apigateway update-rest-api --rest-api-id <id> \
     --patch-operations op=replace,path=/policy,value='<new-policy-json>'
   ```
2. Add `aws:SourceAccount` or `aws:SourceArn` conditions to scope access.
3. If cross-account access is intentional, use a Deny statement for
   everything except trusted accounts (defense-in-depth).

### For CONFIG_GAP — no WAF Web ACL

1. Create or identify a WAF Web ACL with managed rule groups:
   ```bash
   aws wafv2 create-web-acl --name "<api>-waf" --scope REGIONAL \
     --default-action Allow={} \
     --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName="<api>-waf" \
     --rules file://waf-rules.json --profile <p>
   ```
2. Associate the Web ACL with the API stage:
   ```bash
   aws apigatewayv2 associate-web-acl \
     --web-acl-arn <acl-arn> \
     --resource-arn arn:aws:apigateway:<region>::/restapis/<id>/stages/<stage> \
     --profile <p>
   ```
3. Include the AWS Managed Rules rule groups (CommonRuleSet,
   SQLInjectionRuleSet, XSSProtectionRuleSet) and a rate-based rule.

### For OK

1. No remediation required for the current posture.
2. Recommend verifying the WAF rule groups include rate-based rules.
3. Recommend enabling access logging on the stage for forensic visibility:
   ```bash
   aws apigateway update-stage --rest-api-id <id> --stage-name <stage> \
     --patch-operations op=replace,path=/accessLogSettings/destinationArn,value=<log-group-arn>
   ```

## Domain

AWS CloudOps / API Gateway Security & Compliance.

## Recent AWS features (2024-2026)

- **HTTP API mTLS:** HTTP APIs support mutual TLS via custom domain names — verify mTLS on APIs handling sensitive data.
- **VPC Lattice integration:** HTTP APIs can integrate with VPC Lattice as a private integration — a Lattice-backed API may not appear in standard VPC security group audits.
- **OpenAPI 3.1:** REST and HTTP APIs support OpenAPI 3.1 import — does not change audit logic but may affect how auth configs import from external specs.

## AWS documentation

- **API Gateway Developer Guide** — https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html
- **API Gateway API Reference (v2)** — https://docs.aws.amazon.com/apigatewayv2/latest/api-reference/
- **API Gateway API Reference (v1)** — https://docs.aws.amazon.com/apigateway/latest/api/
- **API Gateway Security** — https://docs.aws.amazon.com/apigateway/latest/developerguide/security.html
- **API Gateway CLI Reference (v1)** — https://docs.aws.amazon.com/cli/latest/reference/apigateway/
- **API Gateway CLI Reference (v2)** — https://docs.aws.amazon.com/cli/latest/reference/apigatewayv2/
- **Blog: HTTP API mTLS** — https://aws.amazon.com/blogs/compute/introducing-mutual-tls-authentication-for-amazon-api-gateway-http-apis/
