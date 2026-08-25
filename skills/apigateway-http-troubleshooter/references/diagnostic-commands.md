# Diagnostic commands - API Gateway HTTP API Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `403 Forbidden`, `{"message":"User is not authorized"}}` | JWT_AUTHORIZER | `get-authorizer`, JWT issuer/audience/identity source |
| `404 Not Found` on a known route | ROUTE_MATCHING / ROUTE_PRIORITY_CATCHALL | `get-routes`, route key match, `$default` catch-all |
| Browser CORS: `Access-Control-Allow-Origin` missing | CORS_MISCONFIG | `get-api` CorsConfiguration (HTTP) or get-method OPTIONS (REST) |
| `502 Bad Gateway` from Lambda proxy | INTEGRATION_LAMBDA_PROXY / PAYLOAD_FORMAT_VERSION | `get-integration` PayloadFormatVersion, Lambda response shape |
| `502` / `504` after ~29 seconds | INTEGRATION_TIMEOUT | Integration timeout setting, backend duration |
| `429 Too Many Requests` | THROTTLING_BURST | Stage/route throttling config |
| Config changed but "not live" | STAGE_DEPLOYMENT | `get-stage` AutoDeploy, deployment history |
| `502` from private integration / VPC link | VPCLINK_CONNECTIVITY | `get-vpc-links`, `elbv2 describe-target-health` |
| Traffic flows but no logs | LOGGING_MISCONFIG | Stage access log settings, execution logging level |
| Lambda receives garbled / base64 body | PAYLOAD_FORMAT_VERSION | Integration PayloadFormatVersion 1.0 vs 2.0 |
| None of the above | UNKNOWN / INSUFFICIENT_DATA | Gather API type, full request/response, integration config |

## Pre-flight: API state and gather-info gate

```bash
# 1. API metadata (type, protocol, endpoint)
aws apigatewayv2 get-api --api-id <api-id> --output json

# 2. All routes (route key, target, authorizer)
aws apigatewayv2 get-routes --api-id <api-id> --output json

# 3. Integration details (type, connection, payload format version)
aws apigatewayv2 get-integration --api-id <api-id> \
  --integration-id <id> --output json

# 4. Stage configuration (auto-deploy, throttling, access logs)
aws apigatewayv2 get-stage --api-id <api-id> --stage-name <stage> --output json

# 5. Authorizer configuration (type, issuer, audience, identity source)
aws apigatewayv2 get-authorizer --api-id <api-id> \
  --authorizer-id <id> --output json

# 6. Recent execution logs (if execution logging enabled)
aws logs filter-log-events \
  --log-group-name /aws/apigateway/<api-id>/<stage> \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"403" OR "502" OR "504" OR "429" OR "ERROR"' \
  --output json

# 7. VPC links (for private integrations)
aws apigatewayv2 get-vpc-links --output json

# 8. CloudWatch 5XX metrics
aws cloudwatch get-metric-statistics --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiId,Value=<api-id> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

### Step 2: JWT Authorizer — 403 Forbidden

```bash
aws apigatewayv2 get-authorizer --api-id <api-id> \
  --authorizer-id <id> --output json | \
  jq '{AuthorizerType, IdentitySource, JwtConfiguration}'
```

### Step 3: Route matching — 404 or wrong route handling

```bash
aws apigatewayv2 get-routes --api-id <api-id> --output json | \
  jq '.Items[] | {RouteKey, RouteId, Target, AuthorizerId}'
```

### Step 4: CORS — browser preflight errors

```bash
# HTTP API: CORS is API-level
aws apigatewayv2 get-api --api-id <api-id> --output json | jq '.CorsConfiguration'
# REST API: CORS is per-resource (mock OPTIONS method)
aws apigateway get-method --rest-api-id <id> --resource-id <rid> \
  --http-method OPTIONS --output json
```

### Step 5: Lambda proxy 502 — payload format version and response shape

```bash
aws apigatewayv2 get-integration --api-id <api-id> \
  --integration-id <id> --output json | \
  jq '{IntegrationType, IntegrationSubtype, PayloadFormatVersion}'
```

### Step 7: Throttling — 429 Too Many Requests

```bash
aws apigatewayv2 get-stage --api-id <api-id> \
  --stage-name <stage> --output json | \
  jq '{DefaultRouteSettings, RouteSettings}'
```

### Step 8: Stage deployment — changes not live (get-stage)

```bash
aws apigatewayv2 get-stage --api-id <api-id> \
  --stage-name <stage> --output json | jq '{AutoDeploy, LastDeploymentStatus}'
```

### Step 8: Stage deployment — changes not live (create-deployment)

```bash
aws apigatewayv2 create-deployment --api-id <api-id> --stage-name <stage>
```

### Step 9: VPC link — private integration 502

```bash
aws apigatewayv2 get-vpc-links --output json | \
  jq '.Items[] | {VpcLinkId, Name, SubnetIds, SecurityGroupIds}'
aws elbv2 describe-target-health --target-group-arn <arn> --output json
```

### Step 10: Logging — no logs despite traffic

```bash
aws apigatewayv2 get-stage --api-id <api-id> \
  --stage-name <stage> --output json | \
  jq '{AccessLogSettings, DefaultRouteSettings: .DefaultRouteSettings.LoggingLevel}'
```

