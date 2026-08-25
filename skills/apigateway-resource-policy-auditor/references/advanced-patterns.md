# Advanced patterns - API Gateway Resource Policy Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

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

## Step 0: Expert knowledge — non-obvious API Gateway behaviors

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


## Recent AWS features (2024-2026)

- **HTTP API mTLS:** HTTP APIs support mutual TLS via custom domain names — verify mTLS on APIs handling sensitive data.
- **VPC Lattice integration:** HTTP APIs can integrate with VPC Lattice as a private integration — a Lattice-backed API may not appear in standard VPC security group audits.
- **OpenAPI 3.1:** REST and HTTP APIs support OpenAPI 3.1 import — does not change audit logic but may affect how auth configs import from external specs.


