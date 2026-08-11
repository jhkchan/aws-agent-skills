# End-to-end usage scenario: apigateway-http-api-deployer

A walkthrough showing the skill producing a deployment plan for a
production HTTP API (v2) with Lambda proxy integration, Cognito JWT
authorizer, CORS, auto-deploy stage, JSON access logging, custom
domain via ACM API mapping, and WAFv2 REGIONAL Web ACL. Demonstrates
the READY_TO_DEPLOY verdict, architecture checklist, and ordered
deploy-command list.

## Input (user prompt)

> Provision a production HTTP API for our orders service. Backend is a
> Lambda function `orders-handler` in us-east-1. Routes are
> GET /health (public), GET /orders, POST /orders,
> GET /orders/{id} (JWT-protected), and ANY /{proxy+} (JWT-protected
> fallback). We need Cognito JWT auth, CORS for
> https://shop.example.com, JSON access logs to CloudWatch, auto-deploy
> on $default, WAF with managed rules + rate limiting, custom domain
> `api.example.com` (apex), and per-route throttle on POST /orders.

## Expected behavior

1. **Pre-flight:** the skill validates the spec — routes (method +
   path, ANY /{proxy+} flagged), integration type (AWS_PROXY Lambda),
   authorization (JWT with HTTPS Cognito issuer + audience verified),
   CORS (explicit origins, Authorization in allowHeaders, OPTIONS in
   allowMethods), custom domain (REGIONAL ACM cert), WAF (REGIONAL).
2. **Route model:** the skill plans explicit routes and notes that
   `ANY /{proxy+}` MUST have a JWT authorizer bound — never NONE auth
   on the catch-all.
3. **JWT authorizer:** the skill verifies the issuer URL has a
   trailing slash (Cognito hard requirement) and that the audience
   matches the Cognito app client id. It warns about 300s default
   cache TTL if revocation lag matters.
4. **CORS:** the skill plans `allowOrigins=https://shop.example.com`,
   `allowCredentials=true`, `Authorization` in `allowHeaders`,
   `OPTIONS` in `allowMethods`. It synthesizes preflight responses
   (no manual `OPTIONS` routes).
5. **Stage auto-deploy:** the skill keeps `auto-deploy: true` on
   `$default` and warns NOT to add a `AWS::ApiGatewayV2::Deployment`
   resource on top (races with auto-deploy → drift).
6. **Verdict:** READY_TO_DEPLOY — all 10 checklist dimensions pass.

## Expected output

```text
API_SPEC: prod-orders-http-api
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Type: HTTP (v2)
  Endpoint: REGIONAL (us-east-1)
  Routes:
    - GET /health [NONE]
    - GET /orders [JWT]
    - POST /orders [JWT]
    - GET /orders/{id} [JWT]
    - ANY /{proxy+} [JWT]
  Integrations:
    - Lambda proxy: orders-handler
  Authorization: JWT (issuer https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xyz/, audience orders-app-client)
  CORS: allowOrigins=https://shop.example.com, allowMethods=GET,POST,OPTIONS, allowHeaders=Authorization,Content-Type, allowCredentials=true, maxAge=600
  Stage: '$default' (auto-deploy=true)
  WAF: arn:aws:wafv2:us-east-1:111111111111:regional/webacl/orders-http-waf/qrs-012
  Custom domain: api.example.com (ACM cert us-east-1, API mapping key '')
  Logging: CloudWatch JSON access logs to /aws/apigateway/prod-orders-http
CHECKLIST:
  [x] Type: HTTP (v2) — no usage plans / mapping templates needed
  [x] Endpoint: REGIONAL — consumers in us-east-1
  [x] Routes: GET /health (public), JWT-protected CRUD, greedy ANY with JWT
  [x] Integrations: AWS_PROXY Lambda — no transform needed
  [x] Authorization: JWT with HTTPS Cognito issuer + audience verified
  [x] CORS: explicit origins, Authorization header, OPTIONS included
  [x] Stage: auto-deploy=true (no AWS::ApiGatewayV2::Deployment resource)
  [x] Access logging: JSON with requestId, routeKey, status, latency
  [x] WAF: REGIONAL Web ACL with CommonRuleSet + rate-based rule
  [x] Custom domain: api.example.com + API mapping (empty key = apex)
  [x] Throttle: 1000 rps / 500 burst default; 100/200 on POST /orders
  [x] lambda:AddPermission granted to apigateway.amazonaws.com
FINDINGS:
  - [INFO] Estimated cost: $1.00/M requests (~70% cheaper than REST API)
  - [INFO] JWT validation offloaded to API Gateway — no Lambda authorizer cost
  - [INFO] Auto-deploy means route changes go live in seconds — no create-deployment needed
  - [WARN] No native usage plans — per-consumer throttling requires WAF keyed on JWT claim
  - [WARN] JWT authorizer caches validated tokens for TTL seconds — revocation lag
DEPLOY_COMMANDS:
  1. aws apigatewayv2 create-api --name prod-orders-http --protocol-type HTTP
  2. aws apigatewayv2 create-authorizer --authorizer-type JWT --identity-source '$request.header.Authorization' --jwt-configuration audience=orders-app-client,issuer=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xyz/
  3. aws apigatewayv2 create-integration --integration-type AWS_PROXY --integration-method POST --integration-uri arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:111111111111:function:orders-handler/invocations
  4. aws apigatewayv2 create-route (GET /health, GET /orders, POST /orders, GET /orders/{id}, ANY /{proxy+})
  5. aws apigatewayv2 update-route (bind JWT authorizer on every route except /health)
  6. aws lambda add-permission --function-name orders-handler --statement-id apigw-v2-invoke --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn arn:aws:execute-api:us-east-1:111111111111:<api-id>/*/*
  7. aws apigatewayv2 update-api --cors-configuration allowOrigins=https://shop.example.com,allowMethods=GET,POST,OPTIONS,allowHeaders=Authorization,Content-Type,allowCredentials=true,maxAge=600
  8. aws apigatewayv2 update-stage --stage-name '$default' --auto-deploy true --access-log-settings DestinationArn=arn:aws:logs:us-east-1:111111111111:log-group:/aws/apigateway/prod-orders-http,Format=...
  9. aws apigatewayv2 update-route --route-id <post-orders-id> --route-settings throttlingRateLimit=100,throttlingBurstLimit=200
  10. aws apigatewayv2 create-domain-name --domain-name api.example.com --domain-name-configurations certificateArn=arn:aws:acm:us-east-1:111111111111:certificate/abc-123,securityPolicy=TLS_1_2
  11. aws apigatewayv2 create-api-mapping --domain-name api.example.com --api-id <api-id> --stage '$default' --api-mapping-key ''
  12. aws apigatewayv2 associate-web-acl --web-acl-arn arn:aws:wafv2:us-east-1:111111111111:regional/webacl/orders-http-waf/qrs-012 --resource-arn arn:aws:apigateway:us-east-1::/apis/<api-id>/stages/$default
```

## Verification (run after deploy)

```bash
aws apigatewayv2 get-routes --api-id <id> --query 'Items[*].[RouteKey,AuthorizationType,Target]'
aws apigatewayv2 get-authorizer --api-id <id> --authorizer-id <auth-id>
aws apigatewayv2 get-api --api-id <id> --query 'CorsConfiguration'
aws apigatewayv2 get-stage --api-id <id> --stage-name '$default' --query '[AutoDeploy,AccessLogSettings]'

curl -i https://<api-id>.execute-api.us-east-1.amazonaws.com/health
curl -i -H "Authorization: Bearer <jwt>" https://<api-id>.execute-api.us-east-1.amazonaws.com/orders
curl -i https://api.example.com/health  # via custom domain
```

All routes return the expected status; the catch-all `ANY /{proxy+}`
returns 401 without a JWT (confirming the authorizer is bound to the
catch-all, not just to the explicit verbs).
