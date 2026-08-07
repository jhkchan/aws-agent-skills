# End-to-end usage scenario: apigateway-rest-deployer

A walkthrough showing the skill producing a deployment plan for a
production REST API with Lambda proxy integration, Cognito authorizer,
usage plan with API keys, WAFv2, canary deployment, and a custom domain.
Demonstrates the READY_TO_DEPLOY verdict, architecture checklist, and
ordered deploy-command list.

## Input (user prompt)

> Provision a production REST API for our orders service. Backend is a
> Lambda function `orders-handler` in us-east-1. Resources are
> /orders [GET, POST] and /orders/{id} [GET, PUT, DELETE]. We need
> Cognito user pool auth, per-consumer rate limiting via usage plan with
> API keys, WAF with managed rules + rate limiting, JSON access logs to
> CloudWatch, and canary rollout at 10 percent. Custom domain
> `api.example.com` with base path `v1`.

## Expected behavior

1. **Pre-flight:** The skill validates the spec — API type (REST),
   endpoint type (REGIONAL), integration type (AWS_PROXY Lambda),
   authorization (COGNITO_USER_POOLS), usage plan + API keys, WAF
   scope (REGIONAL), custom domain + ACM cert.
2. **Resource/method layout:** Plans /orders with GET (list) + POST
   (create), and /orders/{id} with GET, PUT, DELETE. Verifies ANY
   method is NOT used (would expose all verbs).
3. **Authorization:** Plans Cognito authorizer with caching TTL of 300
   seconds (default — accepts 5-minute revocation lag for cost savings).
4. **Usage plan:** Plans `prod-consumer-plan` with rate=100, burst=200,
   quota=1M/month. Plans at least one API key linked to the plan.
5. **Deployment discipline:** Plans `create-deployment` as the FINAL
   step (after all method/integration/authorizer config). Without this,
   changes are not live.
6. **Verdict:** READY_TO_DEPLOY — all 14 checklist dimensions pass.

## Expected output

```text
API_SPEC: prod-orders-api
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Type: REST (v1)
  Endpoint: REGIONAL (us-east-1)
  Resources:
    - /orders [GET (list), POST (create)]
    - /orders/{id} [GET (read), PUT (update), DELETE (delete)]
  Integration: AWS_PROXY (Lambda: orders-handler)
  Authorization: COGNITO_USER_POOLS (user pool: prod-shoppers-pool, TTL 300s)
  Usage plan: prod-consumer-plan, rate=100, burst=200, quota=1M/month
  API keys: required on all methods
  WAF: arn:aws:wafv2:us-east-1:111111111111:regional/webacl/orders-waf/qrs-012
  Custom domain: api.example.com (ACM cert in us-east-1, base path v1)
  Logging: CloudWatch JSON access logs to /aws/apigateway/prod-orders-api
  Canary: enabled at 10% traffic shifting
CHECKLIST:
  [x] Type: REST (v1) — usage plans, mapping templates, resource policies
  [x] Endpoint: REGIONAL — consumers in us-east-1
  [x] Resources: /orders, /orders/{id} with explicit verbs (no ANY)
  [x] Integration: AWS_PROXY Lambda — no mapping template needed
  [x] Authorization: COGNITO_USER_POOLS — authorizer configured
  [x] Usage plan: prod-consumer-plan linked to prod stage with API key
  [x] Stage throttling: 1000 rps / 500 burst default
  [x] WAF: REGIONAL Web ACL with CommonRuleSet + rate-based rule
  [x] VPC Link: N/A (Lambda integration)
  [x] Canary: 10% traffic shifting enabled
  [x] Access logging: JSON format with $context.requestId, status, latency
  [x] Custom domain: api.example.com + base path v1 mapping
  [x] lambda:AddPermission: granted to apigateway.amazonaws.com principal
  [x] create-deployment: emitted as final step
FINDINGS:
  - [INFO] Estimated cost: $3.50/M requests + Lambda + $5/WAF/month
  - [INFO] Cognito authorizer caches JWT 300s — lower TTL if revocation lag matters
  - [WARN] Account-level default throttle (10K rps) is shared across all APIs in us-east-1
DEPLOY_COMMANDS:
  1. aws apigateway create-rest-api --name prod-orders-api --endpoint-configuration types=REGIONAL
  2. aws apigateway create-resource (root /, then /orders, /orders/{id})
  3. aws apigateway put-method (GET, POST on /orders; GET, PUT, DELETE on /orders/{id})
  4. aws apigateway create-authorizer --type COGNITO_USER_POOLS --provider-arns <pool-arn>
  5. aws apigateway put-integration --type AWS_PROXY --uri <lambda-arn>
  6. aws lambda add-permission --principal apigateway.amazonaws.com --action lambda:InvokeFunction
  7. aws apigateway create-usage-plan --throttle burstLimit=200,rateLimit=100 --quota limit=1000000,period=MONTH
  8. aws apigateway create-api-key --enabled
  9. aws apigateway create-usage-plan-key --usage-plan-id <plan> --key-id <key>
  10. aws wafv2 create-web-acl --scope REGIONAL --region us-east-1
  11. aws apigateway create-deployment --rest-api-id <id> --stage-name prod
  12. aws apigatewayv2 associate-web-acl (WAF ARN to stage ARN)
  13. aws apigateway update-stage (canary 10% + access logging JSON)
  14. aws apigateway create-domain-name + create-base-path-mapping (api.example.com/v1)
```

## Post-deployment verification

After running the deploy commands, verify the API is correctly
provisioned and the security posture is enforced:

```bash
# Verify stage is deployed
aws apigateway get-stage --rest-api-id <id> --stage-name prod

# Verify all methods have Cognito authorization (NOT NONE)
aws apigateway get-resources --rest-api-id <id> \
  --query 'items[*].resourceMethods[*].[httpMethod,authorizationType,authorizerId]'

# Verify usage plan and linked API keys
aws apigateway get-usage-plans --query 'items[?apiStages[?apiId==`<id>`]]'
aws apigateway get-usage-plan-keys --usage-plan-id <plan-id>

# Verify WAF is associated with the stage
aws apigatewayv2 get-web-acl-for-resource \
  --resource-arn arn:aws:apigateway:us-east-1::/restapis/<id>/stages/prod

# Verify access logging is configured
aws apigateway get-stage --rest-api-id <id> --stage-name prod \
  --query 'accessLogSettings'

# Verify canary configuration
aws apigateway get-stage --rest-api-id <id> --stage-name prod \
  --query 'canarySettings'

# Verify custom domain mapping
aws apigateway get-base-path-mappings --domain-name api.example.com

# Test invocation with a valid Cognito JWT
curl -X GET https://api.example.com/v1/orders \
  -H "Authorization: Bearer <valid-jwt>" \
  -H "x-api-key: <valid-key>"
# Expect: HTTP/1.1 200 OK with JSON list of orders

# Test without auth (should be rejected)
curl -X GET https://api.example.com/v1/orders
# Expect: HTTP/1.1 401 Unauthorized — Cognito authorizer enforced
```

## Common pitfalls to verify after deployment

1. **create-deployment is the LAST step.** Without it, all the resource,
   method, integration, and authorizer changes are not live. Operators
   frequently change auth type, see "success" in the console, and walk
   away — the OLD (often insecure) config keeps serving.
2. **API keys required on methods that need per-key throttling.** A
   usage plan without `apiKeyRequired: true` on the methods cannot
   enforce throttling — clients bypass the plan.
3. **Lambda has lambda:InvokeFunction permission for API Gateway.**
   Without `aws lambda add-permission --principal apigateway.amazonaws.com`,
   the integration returns 500 with "Invalid permissions on Lambda
   function."
4. **WAF is REGIONAL scope (not CLOUDFRONT) for REST APIs in-region.**
   CLOUDFRONT-scope WAFs are only for CloudFront distributions. A
   REGIONAL REST API needs a REGIONAL-scope WAF.
5. **ACM cert region matches endpoint type.** REGIONAL API → cert in
   API region. EDGE API → cert in us-east-1. A cert in the wrong region
   blocks custom domain creation.
