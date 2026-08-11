---
description: Provision a production-grade API Gateway HTTP API (v2) with routes, integrations, JWT authorizer, CORS, auto-deploy, and custom domain.
nl_triggers:
  - "create an HTTP API"
  - "provision API Gateway v2"
  - "API Gateway HTTP API"
  - "Lambda proxy HTTP API"
  - "JWT authorizer HTTP API"
  - "OIDC authorizer API Gateway"
  - "CORS configuration API Gateway"
  - "Step Functions HTTP API"
  - "SQS API Gateway integration"
  - "Kinesis API Gateway integration"
  - "VPC link private integration"
  - "auto-deploy stage"
  - "API Gateway custom domain"
  - "REST to HTTP migration"
routes_to: apigateway-http-api-deployer
---

# /aws:deploy-apigateway-http-api

Activate the `apigateway-http-api-deployer` skill and produce a
deployment plan for a production-grade API Gateway HTTP API (v2).

## What it does

Reads a deployment specification (routes, integration targets, JWT
authorizer, CORS, logging, auto-deploy, custom domain, WAF) and
produces an ordered deployment plan with:

1. Pre-flight specification gate — validates routes (method + path,
   including ANY and `{proxy+}`), integration type (AWS_PROXY,
   HTTP_PROXY, VPC_LINK, STEP_FUNCTION, SQS, KINESIS), authorization
   model (JWT / AWS_IAM / NONE). Blocks deployment
   (PREREQUISITES_MISSING) on missing fields.
2. HTTP API vs REST API feature fit — confirms HTTP API is correct
   (no usage plans, mapping templates, resource policies, EDGE, or
   Lambda authorizers needed).
3. Route model — flat `(method, path)` list. Flags `ANY /{proxy+}` +
   `NONE` auth as a critical security risk.
4. Integration targets — Lambda proxy (AWS_PROXY), HTTP_PROXY, VPC
   link (NLB), direct AWS integrations (Step Functions
   START_EXECUTION / START_SYNC_EXECUTION, SQS SendMessage, Kinesis
   PutRecord). Configures `lambda:AddPermission` for the API Gateway
   principal.
5. JWT authorizer — OpenID Connect / Cognito issuer + audience with
   trailing-slash and HTTPS verification.
6. CORS — API-level allowOrigins, allowMethods (incl. OPTIONS),
   allowHeaders (incl. Authorization for JWT routes),
   allowCredentials.
7. Stage auto-deploy — `$default` (auto-deploy=true) or named stage
   with explicit `auto-deploy` and `deployment-id`.
8. Access logging — JSON `$context` to CloudWatch Logs.
9. Custom domain — ACM cert (REGIONAL only) + API mapping.
10. WAFv2 Web ACL — REGIONAL scope, associated with stage.
11. Throttle — per-route and stage default (no usage plans on v2).

Emits a deterministic deployment plan per API:

```text
API_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Type / Endpoint / Routes / Integrations / Authorization /
  CORS / Stage / WAF / Custom domain / Logging
CHECKLIST:
  [x] HTTP API feature fit confirmed
  [x] Routes defined (ANY / {proxy+} flagged)
  [x] Integrations configured (AWS_PROXY / STEP_FUNCTION / ...)
  [x] JWT authorizer with HTTPS issuer + audience verified
  [x] CORS with allowOrigins + Authorization header + OPTIONS
  [x] Stage auto-deploy explicitly set
  ...
FINDINGS:
  - [INFO] Cost estimate ($1.00/M requests)
  - [WARN] No native usage plans — per-consumer throttling via WAF
DEPLOY_COMMANDS:
  <ordered list of aws apigatewayv2 commands>
```

## When to invoke

Provide a deployment spec and ask any of:

- "create an HTTP API with Lambda proxy"
- "provision an API Gateway v2 with Cognito JWT auth"
- "set up Step Functions direct integration on HTTP API"
- "deploy a VPC link to my NLB from HTTP API"
- "configure CORS on my HTTP API"
- "enable auto-deploy on my HTTP API stage"
- "map a custom domain to my HTTP API"
- "migrate from REST API to HTTP API"

A bare route list + integration + "deploy HTTP API" also routes here
via the orchestrator.

## Inputs

- **Required:** routes (method + path, including ANY / {proxy+}),
  integration_type (AWS_PROXY / HTTP_PROXY / VPC_LINK / STEP_FUNCTION
  / SQS / KINESIS), authorization (JWT / AWS_IAM / NONE) with issuer +
  audience for JWT.
- **Optional:** cors_configuration, auto-deploy flag, deployment-id
  (for pinned stages), access_log_group, custom_domain,
  acm_certificate_arn, waf_web_acl_arn, throttle_per_route.

## Outputs

- One VERDICT block per API (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- ARCHITECTURE summary with type/endpoint/routes/integrations/auth/
  CORS/stage/WAF/domain/logging.
- CHECKLIST with all 10 deployment dimensions validated.
- FINDINGS with cost estimates and HTTP-API-specific warnings (no
  usage plans, no EDGE, etc.).
- DEPLOY_COMMANDS with ordered `aws apigatewayv2` and
  `aws lambda add-permission` commands.

## Related

- `/aws:deploy-apigateway-rest` for the v1 REST API plan when HTTP API
  feature fit fails (needs usage plans, mapping templates, EDGE, or
  Lambda authorizers).
- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 1 Deploy specialist for API Gateway HTTP APIs).
- `/aws:audit-apigateway-resource-policy` for post-deployment security
  auditing.
- `/aws:audit-wafv2-web-acl` for rule-level WAF analysis.
