# REST vs HTTP API and Authorization Reference

Supplementary reference for the API Gateway REST Deployer skill. Use when
choosing between REST API (v1) and HTTP API (v2), designing authorization,
configuring Lambda authorizers, or mapping Cognito user pools to API
methods.

## REST API (v1) vs HTTP API (v2) — full comparison

| Dimension | REST API (v1) | HTTP API (v2) |
|---|---|---|
| Cost per million requests | $3.50 | $1.00 |
| Latency | Higher (more features per request) | ~30% lower than REST |
| Mapping templates (VTL) | Yes | No |
| Usage plans | Yes | No |
| API keys | Yes | No (use Lambda for throttling) |
| Resource policies | Yes | No |
| Authorization types | AWS_IAM, COGNITO_USER_POOLS, CUSTOM | JWT, IAM |
| EDGE endpoint (CloudFront) | Yes | No |
| PRIVATE endpoint | Yes | Yes |
| REGIONAL endpoint | Yes (default) | Yes (only type) |
| WAF association | Yes | Yes |
| Canary deployments | Yes (stage) | Yes (stage) |
| Custom domains | Yes | Yes |
| Stage variables | Yes | Yes |
| WebSocket API | Yes (separate API type) | Yes (separate) |
| OpenAPI import | 2.0, 3.0 | 3.0, 3.1 |
| Request validation | Yes (schema-based) | Limited |
| Migration path | — | Re-create (no in-place conversion) |

## Decision tree — REST or HTTP API

```
Need usage plans with API keys for per-consumer quotas?
  → REST API

Need mapping templates (XML/JSON transform)?
  → REST API

Need EDGE endpoint for global latency optimization?
  → REST API

Need resource policies (cross-account access control)?
  → REST API

Need PRIVATE endpoint with VPC endpoint policy?
  → REST API (HTTP API also supports PRIVATE, but REST is more flexible)

Pure Lambda proxy with JWT auth, no transforms?
  → HTTP API (cheaper, faster, simpler)

Microservice with IAM auth (sigv4) only?
  → HTTP API (cheaper)

Mixed — need mapping templates on some routes, not others?
  → REST API (HTTP API has no mapping templates at all)
```

## HTTP API cost savings

For a workload with 100M requests/month:
- REST API: 100M × $3.50/M = $350/month
- HTTP API: 100M × $1.00/M = $100/month
- Savings: $250/month, $3000/year

The savings compound across multiple APIs. For organizations running
many microservices, the cost difference justifies the migration effort
when the HTTP API feature set suffices.

## Authorization model comparison

### AWS_IAM (sigv4)

**When to use:** Service-to-service, internal APIs, AWS SDK clients.

**How it works:** Caller signs the request with AWS credentials using
sigv4. API Gateway validates the signature against the caller's IAM
identity-based policy AND the API's resource policy (intersection for
cross-account, union for same-account).

**Pros:**
- No additional service needed
- Works with all AWS SDKs out of the box
- Short-lived credentials via STS

**Cons:**
- Not user-friendly (browsers cannot easily produce sigv4)
- Cross-account requires both identity and resource policy alignment

### COGNITO_USER_POOLS

**When to use:** User-facing apps (web, mobile), B2C APIs.

**How it works:** Client obtains JWT from Cognito (login flow). Sends
`Authorization: Bearer <jwt>` to API Gateway. API Gateway validates the
JWT signature against the Cognito user pool's JWKS.

**Pros:**
- User-facing auth with no custom code
- Built-in user management, password reset, MFA
- Federated identity (Google, Facebook, SAML, OIDC)

**Cons:**
- Authorizer caches JWT for 300 seconds default (revoked tokens still work)
- Requires user pool management

### CUSTOM (Lambda authorizer)

**When to use:** Flexible auth (SAML, OAuth introspection, custom logic,
multi-tenant routing, request-shape-based decisions).

**Types:**
- **Token authorizer:** Receives the `Authorization` header. Returns IAM
  policy. Good for Bearer tokens.
- **Request authorizer:** Receives the full request (headers, query, path,
  body summary). Returns IAM policy. Good for multi-tenant, HMAC, signed
  query string.

**Lambda authorizer contract:**
```javascript
exports.handler = async (event) => {
  const token = event.headers.Authorization;
  const principal = validateToken(token);
  if (!principal) {
    return { principalId: 'unauthorized', policyDocument: { Version: '2012-10-17', Statement: [{Effect: 'Deny', Action: 'execute-api:Invoke', Resource: '*'}] }};
  }
  return {
    principalId: principal.id,
    policyDocument: {
      Version: '2012-10-17',
      Statement: [{Effect: 'Allow', Action: 'execute-api:Invoke', Resource: event.methodArn}]
    },
    context: { userId: principal.id, tenantId: principal.tenant } // passed to integration
  };
};
```

**Authorizer caching:** Default 300 seconds. Set `authorizerResultTtlInSeconds`
based on the revocation window. TTL=0 disables caching (every request
calls the Lambda — higher cost, immediate revocation).

### NONE

**When to use:** Public health checks, public documentation, public
download endpoints, OPTIONS preflight for CORS.

**When NEVER to use:** Any endpoint with sensitive data, destructive
operations, or rate-limiting concerns. NONE + apiKeyRequired is NOT
authenticated — the API key is a usage-plan identifier, not auth.

## Resource policy and cross-account access

REST APIs support a resource policy (similar to S3, KMS, Secrets Manager).
HTTP APIs do NOT.

**Cross-account access (REST API):**
```json
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::<other-account>:root"},
    "Action": "execute-api:Invoke",
    "Resource": "arn:aws:execute-api:<region>:<account>:<api-id>/prod/GET/users",
    "Condition": {"StringEquals": {"aws:SourceAccount": "<other-account>"}}
  }]
}
```

For cross-account, both the resource policy AND the caller's IAM identity
policy must allow the call. This is intersection-based for cross-account,
union-based for same-account.

## VPC endpoint policy (PRIVATE endpoints)

For PRIVATE endpoint APIs, the interface VPC endpoint policy controls
access. This is in addition to method authorization:

```json
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "execute-api:Invoke",
    "Resource": "arn:aws:execute-api:<region>:<account>:<api-id>/*",
    "Condition": {"StringEquals": {"aws:SourceVpce": "vpce-xxx"}}
  }]
}
```

A PRIVATE API with NONE auth method but a restrictive VPC endpoint
policy is OK — the VPC endpoint policy is the access control. But a
PRIVATE API with NONE auth and a permissive VPC endpoint policy is a
risk within the VPC.

## ACM certificate regions for custom domains

| API endpoint type | ACM cert region | Notes |
|---|---|---|
| REGIONAL | API's region | Cert and API must be in same region |
| EDGE | us-east-1 | CloudFront reads ACM only from us-east-1 |
| PRIVATE | API's region | Same as REGIONAL |
| HTTP API (always REGIONAL) | API's region | HTTP API does not support EDGE |

**Wildcard certs:** `*.example.com` covers `api.example.com`,
`www.example.com`, etc. but NOT `api.v2.example.com` (two-level
wildcards require separate certs or per-level wildcards).

### Step 1: API type selection — REST (v1) vs HTTP (v2)

| Dimension | REST API (v1) | HTTP API (v2) |
|---|---|---|
| Cost | $3.50/M requests + data transfer | $1.00/M requests (cheaper) |
| Latency | Higher (more features) | Lower (~30% better) |
| Mapping templates | Yes (Velocity/VTL) | No |
| Usage plans + API keys | Yes | No (use Lambda for throttling) |
| Resource policies | Yes | No |
| Authorization | AWS_IAM, COGNITO_USER_POOLS, CUSTOM | JWT, IAM |
| EDGE endpoint | Yes (CloudFront) | No |
| PRIVATE endpoint | Yes | Yes |
| WAF association | Yes | Yes |
| Canary deployments | Yes (stage level) | Yes (stage level) |
| Custom domains | Yes | Yes |
| Migration path | — | Re-create (no in-place conversion) |

**Decision rule:**
- Use HTTP API for: Lambda proxy with JWT auth, simple CRUD, microservices.
- Use REST API for: usage plans with API keys, mapping templates, EDGE
  global deployment, resource policies, existing clients on v1 features.


### Step 5: Authorization

| Type | Use case | Configuration |
|---|---|---|
| `AWS_IAM` | Service-to-service, internal APIs | Caller signs request with sigv4 credentials. |
| `COGNITO_USER_POOLS` | User-facing apps | Caller passes JWT `Authorization: Bearer <token>`. Authorizer validates against Cognito. |
| `CUSTOM` (Lambda) | Flexible auth (SAML, OAuth introspection, custom logic) | Lambda returns IAM policy. Token authorizer (header) or request authorizer (full request). |
| `NONE` | Public endpoints (health checks, public docs) | No auth. Acceptable only for genuinely public data. |

**Cognito authorizer:**
```bash
aws apigateway create-authorizer --rest-api-id <id> \
  --name cognito-auth --type COGNITO_USER_POOLS \
  --provider-arns arn:aws:cognito-idp:<region>:<account>:userpool/<pool-id> \
  --identity-source method.request.header.Authorization
```

**Lambda request authorizer:**
```bash
aws apigateway create-authorizer --rest-api-id <id> \
  --name lambda-auth --type REQUEST \
  --authorizer-uri arn:aws:apigateway:<region>:lambda:path/2015-03-31/functions/arn:aws:lambda:<region>:<account>:function:my-auth/invocations \
  --authorizer-credentials-arn arn:aws:iam::<account>:role:apigw-invoker \
  --identity-source method.request.header.Authorization \
  --identity-validation-expression '^Bearer .+$'
```


