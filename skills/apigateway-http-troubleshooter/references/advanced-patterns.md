# Advanced patterns - API Gateway HTTP API Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset

A failing API Gateway HTTP API is usually a configuration, mapping, or
deployment issue wearing a backend-code costume. The integration is
fine in the majority of cases; the broken thing is route priority, JWT
claim mapping, CORS headers, payload format version, stage deployment,
throttling, or VPC link connectivity. Treat the backend handler as
innocent until the route, authorizer, integration, and stage layers
are proven clean.

## Philosophy

- **The HTTP status code drives the diagnostic order.** A `403` with a
  JWT authorizer means the authorizer denied the request. A `502` with
  a Lambda integration means API Gateway could not parse the response.
  A `504` or `502` after exactly 29 seconds means the integration
  timed out. Routing the symptom to the wrong layer is the #1 source
  of wasted cycles.

- **Payload format version 2.0 is the single most common silent-break
  for Lambda integrations on HTTP APIs.** The v2.0 event wraps the body
  differently, flattens headers, and base64-encodes binary content. A
  handler that worked on a REST API (v1.0) silently breaks on POST
  bodies after migration to HTTP API (v2.0).

- **Route priority evaluation is deterministic but non-obvious.**
  Exact match → greedy (variable) match → `$default`. If `$default` is
  configured, any request not matching an explicit route falls through
  to it, masking undeployed or mis-keyed routes.

- **Stage deployment is mandatory for REST APIs and optional
  (auto-deploy) for HTTP APIs — but auto-deploy can be disabled.** An
  HTTP API stage with `AutoDeploy: false` requires manual
  `create-deployment`.

## Step 0: Non-obvious behaviours that change diagnosis

- **Payload format version 2.0 base64-encodes binary and non-JSON
  bodies.** A handler that does `JSON.parse(event.body)` on a base64
  string throws. Check `event.isBase64Encoded` and decode first, or
  switch to `PayloadFormatVersion: 1.0`.

- **JWT authorizer identity source controls which claim is evaluated.**
  If the client sends the token in a different header than
  `IdentitySource` specifies, the authorizer sees an empty string and
  denies with 403.

- **JWT audience must match the `aud` claim exactly.** Case-sensitive.
  Authorizer `Audience: ["client-1"]` denies a token with
  `aud: ["client-2"]`.

- **Route priority: exact → greedy → `$default`.** `$default` is
  intentional but masks undeployed or mis-keyed routes.

- **The 29-second integration timeout is NOT tunable.** If the backend
  takes longer, API Gateway returns 504 (REST) or 502 (HTTP). Move
  long-running work to async.

- **`AutoDeploy: true` may not pick up authorizer or access-log
  changes.** When in doubt, run `create-deployment` explicitly.

- **CORS on HTTP APIs is API-level (`cors-configuration`); on REST
  APIs it is per-resource (mock OPTIONS method).** Missing
  `AllowMethods: [OPTIONS]` means preflight fails.

- **VPC link integrations require the NLB target group to be healthy.**
  The VPC link is transparent; always `describe-target-health`.

- **Access logging and execution logging are separate.** Access logs
  record every request; execution logs record API Gateway internals.
  Operators who "don't see logs" often enabled one but not the other.

## Expert heuristic

Three heuristics separate a senior API Gateway engineer from a
generalist:

### Heuristic 1: Payload format version determines body encoding

- **v2.0** → body may be base64-encoded (`isBase64Encoded: true`),
  headers are flat, `requestContext` is simplified. Handler must check
  and decode.
- **v1.0** → body is a raw string, headers are multi-value,
  `requestContext` is the REST API shape.
- The silent break: a handler migrated from REST API (v1.0) to HTTP
  API (v2.0) fails on POST bodies because `JSON.parse(event.body)`
  encounters a base64 string. The error appears as 502 Bad Gateway.

### Heuristic 2: JWT claim mapping is issuer + audience + identity source

- `Issuer` must match the token's `iss` exactly (scheme + trailing
  slash). Cognito issuers are
  `https://cognito-idp.<region>.amazonaws.com/<user-pool-id>`.
- `Audience` must match at least one value in the token's `aud` claim.
  Empty `Audience` accepts any audience (insecure).
- `IdentitySource` maps the request header to the token. A mismatch
  means the authorizer receives an empty string and denies everything.

### Heuristic 3: Route priority evaluation order

- Exact match first (`GET /orders`), then greedy/variable
  (`GET /orders/{id}`), then `$default` (catch-all).
- `$default` masks undeployed routes, mis-keyed routes (case
  sensitivity, trailing slash), and missing methods.
- Diagnostic order: (1) check route exists in config, (2) check stage
  was deployed, (3) check route key for case/slash/method mismatch.

## Configuration dependency graph

```
Client Request
    │
    ▼
┌──────────────────────────────────┐
│  Stage (auto-deploy?)            │── Step 8: STAGE_DEPLOYMENT
│    │                             │
│    ▼                             │
│  Route Matching                  │── Step 3: ROUTE_MATCHING
│  (exact → greedy → $default)     │   ROUTE_PRIORITY_CATCHALL
│    │                             │
│    ▼                             │
│  Authorizer (JWT?)               │── Step 2: JWT_AUTHORIZER
│  (issuer, audience, id source)   │
│    │                             │
│    ▼                             │
│  CORS Check (preflight OPTIONS)  │── Step 4: CORS_MISCONFIG
│    │                             │
│    ▼                             │
│  Throttling (rate, burst)        │── Step 7: THROTTLING_BURST
│    │                             │
│    ▼                             │
│  Integration                     │── Step 5: PAYLOAD_FORMAT_VERSION
│  ┌─ Lambda Proxy (1.0 vs 2.0) ─┐ │   INTEGRATION_LAMBDA_PROXY
│  └─────────────────────────────┘ │── Step 6: INTEGRATION_TIMEOUT
│  ┌─ VPC Link → NLB → TG ───────┐ │── Step 9: VPCLINK_CONNECTIVITY
│  └─────────────────────────────┘ │
│    │                             │
│    ▼                             │
│  Logging (access vs execution)   │── Step 10: LOGGING_MISCONFIG
└──────────────────────────────────┘
```

