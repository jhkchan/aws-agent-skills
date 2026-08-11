# JWT Authorizer, CORS, Custom Domain, Auto-Deploy Reference (HTTP API / v2)

Supplementary reference for the API Gateway HTTP API Deployer skill.
Use when configuring a JWT authorizer against an OIDC provider or
Cognito, tuning CORS for browser clients, mapping a custom domain via
ACM, or reasoning about auto-deploy stage lifecycle.

## JWT authorizer internals

HTTP API JWT authorizers validate the `Authorization: Bearer <token>`
header against a JWKS published by an OpenID Connect issuer.

```text
client sends Authorization: Bearer <jwt>
  → API Gateway extracts the token from identity-source
  → API Gateway reads <issuer>/.well-known/openid-configuration
  → API Gateway fetches <jwks_uri> from the OIDC config
  → API Gateway verifies signature, iss, aud, exp, nbf
  → on success: forwards request to integration with claims in $context.authorizer.jwt.claims
  → on failure: returns 401 Unauthorized, integration NOT invoked
```

**Issuercurl check (verify before creating the authorizer):**
```bash
curl -s https://cognito-idp.us-east-1.amazonaws.com/us-east-1_abc123/.well-known/openid-configuration | jq .
```

The `issuer` field of the response is the canonical issuer URL — copy
it verbatim into `jwt-configuration.issuer`.

### Cognito user pool specifics

| Field | Value | Notes |
|---|---|---|
| Issuer | `https://cognito-idp.<region>.amazonaws.com/<pool-id>/` | Trailing slash REQUIRED |
| Audience | App client id (e.g., `1a2b3c4d...`) | Cognito tokens use `client_id`, not `aud` |
| Identity source | `$request.header.Authorization` | Default, almost always correct |
| Authorizer TTL | 300s (recommended for production) | Default is 0 (no cache) |

The trailing slash on the issuer URL is a hard AWS requirement for
Cognito. A missing slash returns "Invalid JWT configuration" on
`create-authorizer` and is the #1 cause of authorizer creation failure.

### Third-party OIDC (Auth0, Okta, Ping)

| Field | Value |
|---|---|
| Issuer | The exact `issuer` value from the provider's OpenID configuration |
| Audience | The exact `aud` claim value the provider emits |
| Identity source | `$request.header.Authorization` |
| Authorizer TTL | 300s recommended |

The audience for third-party OIDC MUST match the `aud` claim exactly.
Cognito uses `client_id` which API Gateway recognizes automatically —
third-party providers do not get the same treatment.

### Authorizer binding per route

```bash
aws apigatewayv2 update-route --api-id <id> --route-id <rid> \
  --authorizer-id <auth-id> --authorization-type JWT
```

- Routes with `authorization-type NONE` are public. Health-check routes
  are the legitimate public case.
- Routes with `authorization-type AWS_IAM` use sigv4 (no authorizer ID
  needed). Useful for service-to-service.
- A route can have only ONE authorizer binding. Multi-tenant auth
  patterns requiring chained validators need REST API with a Lambda
  authorizer.

### Token revocation lag

With TTL > 0, API Gateway caches the validated token for the TTL
duration. A revoked token continues to work until the cache entry
expires. For sensitive APIs (payments, admin), set TTL=0 and accept
the higher authorizer invocation cost. For high-volume public APIs
(e-commerce browse), 300s TTL is appropriate.

Cognito token revocation via the `/oauth2/revoke` endpoint invalidates
refresh tokens, not the access token itself. The access token is valid
until its `exp` claim (default 1 hour).

## CORS deep dive

HTTP API CORS is API-level, not per-route. API Gateway synthesizes
`OPTIONS` preflight responses for any route matching the configured
`allowOrigins`.

### Configuration

```bash
aws apigatewayv2 update-api --api-id <id> \
  --cors-configuration \
    allowOrigins=https://app.example.com,https://admin.example.com,\
allowMethods=GET,POST,PUT,DELETE,OPTIONS,\
allowHeaders=Authorization,Content-Type,X-Request-Id,\
exposeHeaders=X-Request-Id,X-Trace-Id,\
maxAge=600,\
allowCredentials=true
```

### Common CORS failures

| Symptom | Cause | Fix |
|---|---|---|
| Browser blocks preflight with "no `Access-Control-Allow-Origin`" | `allowOrigins` does not include the request origin | Add origin explicitly |
| Browser blocks request with "credentials flag true but `Allow-Origin` wildcard" | `allowCredentials=true` + `allowOrigins=*` | List explicit origins |
| Browser cannot send Bearer token | `Authorization` missing from `allowHeaders` | Add `Authorization` to allowHeaders |
| Preflight succeeds but POST fails | `POST` missing from `allowMethods` | Add POST (and OPTIONS) to allowMethods |
| Custom response header invisible to JS | Header not in `exposeHeaders` | Add to exposeHeaders |

### Wildcard subdomain origins (2025)

`cors-configuration` accepts up to 100 origins and supports
`https://*.example.com` subdomain wildcards for tenant apps. Wildcard
subdomains and `allowCredentials=true` ARE compatible — the wildcard
matches one subdomain level (`https://tenantA.example.com` matches,
`https://a.b.example.com` does not).

### When to add explicit OPTIONS routes

API Gateway synthesizes preflight responses automatically. Add an
explicit `OPTIONS /path` route with a MOCK integration ONLY when:
- You need to override the synthesized response with custom headers.
- You need a non-standard preflight body.

Otherwise, adding `OPTIONS` routes pollutes the route table and
overrides the synthesized response — a frequent source of confusing
CORS bugs.

## Custom domain via API mapping

HTTP API uses **API mappings** (not REST API's base path mappings):

```bash
aws apigatewayv2 create-domain-name --domain-name api.example.com \
  --domain-name-configurations certificateArn=arn:aws:acm:<region>:<account>:certificate/<id>,securityPolicy=TLS_1_2

aws apigatewayv2 create-api-mapping --domain-name api.example.com \
  --api-id <api-id> --stage '$default' --api-mapping-key ''
```

### Mapping semantics

| `api-mapping-key` | URL → stage | Notes |
|---|---|---|
| `''` (empty) | `api.example.com/` → `$default` | Apex mapping |
| `v1` | `api.example.com/v1/` → stage | Sub-path mapping |
| `v1/users` | `api.example.com/v1/users/` → stage | Deep sub-path |

Multiple API mappings on the same domain route different paths to
different APIs. This is how `api.example.com/v1` and `api.example.com/v2`
can point at different HTTP APIs (e.g., during a v1 → v2 migration).

### ACM cert requirements

- **REGIONAL only.** HTTP API does not support EDGE custom domains. The
  cert MUST be in the API's region.
- The cert must cover the domain (SAN or wildcard).
- HTTP API does not support mTLS at the API level — mTLS is configured
  on the **domain name** via `mutualTlsAuthentication`. The trust store
  is an S3 URI pointing to a CA bundle.

### DNS wiring

The custom domain returns a CloudFront-style DNS name (e.g.,
`d-abc123.execute-api.us-east-1.amazonaws.com`). Create an Alias record
in Route53 pointing the friendly hostname at this target. The Alias,
not a CNAME, is required for zone-apex mappings (`api.example.com`).

## Auto-deploy stage lifecycle

The `$default` stage is created with `auto-deploy: true` when the API
is created. Every route, integration, and authorizer change goes live
within seconds — there is no `create-deployment` step.

### Lifecycle states

| Stage config | Effect |
|---|---|
| `auto-deploy: true`, no `deployment-id` | Live, follows latest config (default) |
| `auto-deploy: false`, `deployment-id: <id>` | Pinned to a specific deployment |
| `auto-deploy: false`, no `deployment-id` | 404 for every route |

### Pinning a stage (gated release)

```bash
aws apigatewayv2 create-deployment --api-id <id>
aws apigatewayv2 update-stage --api-id <id> --stage-name prod \
  --auto-deploy false --deployment-id <deployment-id>
```

Swap deployments by calling `update-stage` with a new `deployment-id`.
To roll back, point at a prior deployment-id (if still referenced by
another stage; otherwise it is gone).

### Race with Infrastructure-as-Code

A common failure mode in CloudFormation / CDK / SAM / Terraform:

```text
CloudFormation deploys AWS::ApiGatewayV2::Api, ::Route, ::Integration
  → $default stage (auto-deploy=true) makes them live in seconds
CloudFormation then deploys AWS::ApiGatewayV2::Deployment
  → creates another deployment, but $default already served traffic
  → drift between CloudFormation's view and the live config
```

**Resolution:** pick ONE model:
- Continuous deployment: `auto-deploy: true`, omit
  `AWS::ApiGatewayV2::Deployment` from the template.
- Gated release: `auto-deploy: false`, include
  `AWS::ApiGatewayV2::Deployment` with explicit `DependsOn` on routes
  and integrations.

## Access logging $context variables

Useful `$context` fields for JSON access logs:

| Variable | Meaning |
|---|---|
| `$context.requestId` | Unique request ID |
| `$context.routeKey` | e.g., `POST /users` |
| `$context.stage` | Stage name |
| `$context.status` | HTTP status code |
| `$context.responseLength` | Response body length |
| `$context.integrationLatency` | Backend latency in ms |
| `$context.authorizer.jwt.claims.<claim>` | JWT claim value |
| `$context.identity.sourceIp` | Caller IP |
| `$context.identity.userAgent` | User agent |
| `$context.error.message` | Error message (if any) |
| `$context.error.responseType` | Error type |

Recommended JSON format (single line, escape quotes):
```json
{"requestId":"$context.requestId","routeKey":"$context.routeKey","status":$context.status,"latency":$context.integrationLatency,"ip":"$context.identity.sourceIp","errorMessage":"$context.error.message"}
```

CloudWatch Logs Insights query example:
```
fields @timestamp, routeKey, status, latency
| filter status >= 400
| stats count() by routeKey, status
```

## AWS documentation

- **JWT authorizer for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html
- **CORS for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-cors.html
- **Custom domain names for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-custom-domain-names.html
- **Stages for HTTP APIs (auto-deploy)** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-stages.html
- **Access logging for HTTP APIs** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-logging.html
