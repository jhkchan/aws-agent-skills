# HTTP API vs REST API Quick Reference

Supplementary reference for the API Gateway HTTP API Troubleshooter
skill. Loaded on-demand when a diagnostic needs to distinguish HTTP API
(apigatewayv2) from REST API (apigateway) behaviour, CLI commands,
configuration models, or feature support.

## CLI command comparison

| Operation | HTTP API (apigatewayv2) | REST API (apigateway) |
|---|---|---|
| Get API | `aws apigatewayv2 get-api --api-id <id>` | `aws apigateway get-rest-api --rest-api-id <id>` |
| List routes / resources | `aws apigatewayv2 get-routes --api-id <id>` | `aws apigateway get-resources --rest-api-id <id>` |
| Get integration / method | `aws apigatewayv2 get-integration --api-id <id> --integration-id <id>` | `aws apigateway get-method --rest-api-id <id> --resource-id <id> --http-method <method>` |
| Get stage | `aws apigatewayv2 get-stage --api-id <id> --stage-name <name>` | `aws apigateway get-stage --rest-api-id <id> --stage-name <name>` |
| Get authorizer | `aws apigatewayv2 get-authorizer --api-id <id> --authorizer-id <id>` | `aws apigateway get-authorizer --rest-api-id <id> --authorizer-id <id>` |
| Create deployment | `aws apigatewayv2 create-deployment --api-id <id> --stage-name <name>` | `aws apigateway create-deployment --rest-api-id <id> --stage-name <name>` |
| Get VPC links | `aws apigatewayv2 get-vpc-links` | `aws apigateway get-vpc-links` |
| Update CORS | `aws apigatewayv2 update-api --api-id <id> --cors-configuration ...` | N/A (per-resource mock OPTIONS) |

## Feature comparison

| Feature | HTTP API | REST API |
|---|---|---|
| Deployment model | Auto-deploy (optional per stage) | Manual deployment always required |
| Routing | Route keys (`GET /path`, `$default`, `ANY /path`) | Resource tree + methods |
| Payload format version | 1.0 and 2.0 (default 2.0 for Lambda) | 1.0 only |
| CORS | API-level (`cors-configuration` on the API) | Per-resource (mock OPTIONS method + integration response headers) |
| Authorizers | JWT (Cognito, custom), Lambda | Cognito, Lambda, custom (request/response models) |
| Mapping templates | Not supported | Full request/response mapping templates (Velocity) |
| Throttling | Stage-level and route-level | Stage-level, method-level, usage plans |
| API keys | Not supported | Supported (with usage plans) |
| WAF | Supported | Supported |
| Access logs | JSON or CLF format | JSON or CLF format |
| Execution logs | INFO / ERROR levels | INFO / ERROR levels |
| Integration timeout | 29 seconds (hard cap) | 29 seconds (hard cap) |
| WebSocket | Separate API type (`ProtocolType: WEBSOCKET`) | Not supported |
| Private integrations | VPC link to NLB | VPC link to NLB (different resource model) |

## Payload format version event shape comparison

### v1.0 event (REST API default, HTTP API optional)

```json
{
  "resource": "/orders",
  "path": "/orders",
  "httpMethod": "POST",
  "headers": { "Content-Type": "application/json" },
  "multiValueHeaders": { "Content-Type": ["application/json"] },
  "queryStringParameters": { "filter": "active" },
  "multiValueQueryStringParameters": { "filter": ["active"] },
  "pathParameters": null,
  "body": "{\"orderId\":\"123\"}",
  "isBase64Encoded": false,
  "requestContext": {
    "resourceId": "abc123",
    "resourcePath": "/orders",
    "httpMethod": "POST",
    "stage": "prod",
    "identity": { "sourceIp": "1.2.3.4" }
  }
}
```

### v2.0 event (HTTP API default)

```json
{
  "version": "2.0",
  "routeKey": "POST /orders",
  "rawPath": "/orders",
  "rawQueryString": "filter=active",
  "headers": { "content-type": "application/json" },
  "queryStringParameters": { "filter": "active" },
  "requestContext": {
    "http": {
      "method": "POST",
      "path": "/orders",
      "protocol": "HTTP/1.1",
      "sourceIp": "1.2.3.4"
    },
    "routeKey": "POST /orders",
    "stage": "$default"
  },
  "body": "eyJvcmRlcklkIjoiMTIzIn0=",
  "isBase64Encoded": true
}
```

### Key differences in handler code

| Aspect | v1.0 handler | v2.0 handler |
|---|---|---|
| Body parsing | `JSON.parse(event.body)` — body is raw JSON string | Check `event.isBase64Encoded` first; decode if true, then `JSON.parse` |
| Headers | `event.headers` or `event.multiValueHeaders` | `event.headers` only (flat, no multi-value) |
| HTTP method | `event.httpMethod` | `event.requestContext.http.method` |
| Path | `event.path` | `event.rawPath` or `event.requestContext.http.path` |
| Source IP | `event.requestContext.identity.sourceIp` | `event.requestContext.http.sourceIp` |
| Stage | `event.requestContext.stage` | `event.requestContext.stage` |

## Common migration pitfalls (REST to HTTP API)

1. **Payload format version changes the event shape.** A handler
   written for REST API (v1.0) breaks silently on HTTP API (v2.0)
   because `event.body` may be base64-encoded and `requestContext` is
   restructured. Always set `PayloadFormatVersion: 1.0` on the
   integration during migration, or update the handler.

2. **CORS moves from per-resource to API-level.** REST APIs require a
   mock OPTIONS method per resource. HTTP APIs use a single
   `CorsConfiguration` on the API. The migration is not automatic.

3. **Deployment model changes.** REST APIs require manual
   `create-deployment` after every change. HTTP APIs can auto-deploy.
   But if `AutoDeploy: false` is set, changes are invisible without
   a manual deployment.

4. **Authorizer model differs.** REST APIs support Cognito, Lambda,
   and custom authorizers with request/response templates. HTTP APIs
   support JWT authorizers (simpler, no mapping templates) and Lambda
   authorizers (simplified IAM model).

5. **No mapping templates on HTTP APIs.** REST APIs support Velocity
   mapping templates for request/response transformation. HTTP APIs
   do not — transformation must happen in the backend handler.
