# API Gateway Payload Format & JWT Authorizer Reference Guide

Supplementary reference for the API Gateway HTTP API Troubleshooter
skill. Loaded on-demand when a diagnostic needs payload format version
semantics, JWT claim mapping rules, route priority evaluation order,
or VPC link / NLB connectivity matrix.

## Payload format version comparison

| Property | v1.0 | v2.0 |
|---|---|---|
| Body encoding | Raw string (JSON or otherwise) | May be base64-encoded (`isBase64Encoded: true`) for binary |
| `requestContext` | Full REST API context (resource path, stage vars, identity) | Simplified (HTTP API context, fewer fields) |
| Headers | `headers` (single-value) + `multiValueHeaders` | Flat `headers` (single-value only) |
| `pathParameters` | Populated from `{proxy+}` or `{id}` path variables | Populated from route variables |
| `queryStringParameters` | Single-value | Single-value (no multi-value) |
| `isBase64Encoded` | Present (false for text) | Present (true for binary/large content) |
| Response format | `{statusCode, headers, body, isBase64Encoded}` | Same shape, but `statusCode` must be integer |

### Common payload format version gotchas

- **v2.0 base64 body on POST:** When the client sends a POST body that
  API Gateway classifies as binary (based on Content-Type or content
  inspection), the event arrives with `isBase64Encoded: true` and
  `body` as a base64 string. The handler MUST decode before parsing.
- **v2.0 flat headers:** `event.multiValueHeaders` does not exist on
  v2.0. If multiple values are sent for the same header, only the last
  value is retained. Handlers that iterate `multiValueHeaders` break.
- **Response `statusCode` type:** On v2.0, `statusCode` must be an
  integer. A string `"200"` causes API Gateway to return 502.

## JWT authorizer configuration matrix

| Config field | Effect | Common mistake |
|---|---|---|
| `IdentitySource` | Maps the request header to the JWT | Client sends token in `X-Auth-Token` but config reads `$request.header.Authorization` → 403 |
| `JwtConfiguration.Issuer` | Must match the token's `iss` claim exactly | Cognito URL with wrong pool ID; trailing slash mismatch |
| `JwtConfiguration.Audience` | Must match at least one value in the token's `aud` claim | Wrong client ID; empty list accepts any audience (insecure) |
| `EnableSimpleResponses` | If true, authorizer returns a simple boolean | Complex claim mapping requires custom Lambda authorizer instead |

### Cognito issuer URL format

```
https://cognito-idp.<region>.amazonaws.com/<user-pool-id>
```

No trailing slash. The `iss` claim in the Cognito-issued JWT matches
this URL exactly. A mismatch (wrong region, wrong pool ID, extra slash)
causes every token to be rejected.

### Common JWT failure patterns

| Pattern | Cause | Fix |
|---|---|---|
| All requests 403, issuer matches | Audience mismatch between config and token `aud` claim | Add the token's `aud` value to the authorizer `Audience` |
| All requests 403, audience matches | Identity source header mismatch | Update `IdentitySource` to match client's header name |
| Intermittent 403 | Token expiring; refresh token not used | Client must refresh before expiry |
| 403 only for some routes | Authorizer not attached to all routes | Associate the authorizer with each route individually |

## Route priority evaluation order

API Gateway evaluates routes in this deterministic order:

1. **Exact match:** `GET /orders` matches before `GET /orders/{id}`
2. **Greedy (variable) match:** `GET /orders/{id}` matches before `$default`
3. **`$default`:** Catches anything not matched above

```
GET /orders          → exact match (highest priority)
GET /orders/{id}     → variable match
ANY /{proxy+} (REST) → greedy proxy match
$default (HTTP API)  → catch-all (lowest priority)
```

### Route-key matching rules

- **Case-sensitive:** `POST /Orders` does NOT match `POST /orders`
- **Trailing slash:** `POST /orders/` does NOT match `POST /orders`
- **Method matters:** `PUT /orders` does NOT match `POST /orders`
- **`ANY` method:** Matches all HTTP methods (GET, POST, PUT, etc.)
- **`$default`:** Matches any method and any path on HTTP APIs

## VPC link and NLB connectivity matrix

| Component | What to check | CLI command |
|---|---|---|
| VPC link | Subnet IDs, SG IDs, state | `aws apigatewayv2 get-vpc-links` |
| NLB target group | Target health, target protocol/port | `aws elbv2 describe-target-health` |
| NLB listener | Protocol, port, default action | `aws elbv2 describe-listeners` |
| Integration | ConnectionType (VPC_LINK), ConnectionId, IntegrationURI | `aws apigatewayv2 get-integration` |

### VPC link troubleshooting order

1. Check VPC link state (should be `AVAILABLE`)
2. Check NLB target group health (should have healthy targets)
3. Check VPC link SG allows inbound from NLB listener port
4. Check NLB listener protocol/port matches integration URI
5. Check VPC link subnets are in the same VPC as the NLB
6. Check the backend behind the NLB is actually responding

## HTTP API vs REST API quick comparison

| Feature | HTTP API (apigatewayv2) | REST API (apigateway) |
|---|---|---|
| CLI | `aws apigatewayv2` | `aws apigateway` |
| Routes | Route keys (`GET /path`, `$default`) | Resource tree + methods |
| Deployment | Auto-deploy (optional) | Manual deployment required |
| CORS | API-level (`cors-configuration`) | Per-resource mock OPTIONS |
| Authorizers | JWT, Lambda | Cognito, Lambda, custom |
| Payload format version | 1.0 or 2.0 (default 2.0) | 1.0 only |
| Throttling | Stage and route-level | Stage, method, and usage-plan |
| Integration timeout | 29s (hard cap) | 29s (hard cap) |
| Mapping templates | Not supported | Supported (request/response) |
