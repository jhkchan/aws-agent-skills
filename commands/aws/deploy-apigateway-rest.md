---
description: Provision a production-grade API Gateway REST API with Lambda proxy, authorizers, usage plans, WAF, VPC Link, canary, and custom domain.
nl_triggers:
  - "create a REST API"
  - "provision API Gateway"
  - "Lambda proxy integration"
  - "API Gateway Cognito authorizer"
  - "API Gateway usage plan"
  - "API Gateway rate limiting"
  - "API Gateway VPC Link"
  - "canary deployment API Gateway"
  - "API Gateway custom domain"
  - "REST API vs HTTP API"
  - "API Gateway WAF"
  - "API Gateway access logging"
  - "deploy REST API for Lambda"
  - "API Gateway mapping template"
routes_to: apigateway-rest-deployer
---

# /aws:deploy-apigateway-rest

Activate the `apigateway-rest-deployer` skill and produce a deployment
plan for a production-grade API Gateway REST API.

## What it does

Reads a deployment specification (API type, endpoint type, resource/
method layout, integration type, authorization, throttling, usage plan,
WAF, VPC Link, custom domain, logging, canary) and produces an ordered
deployment plan with:

1. Pre-flight specification gate — validates API type (REST vs HTTP),
   endpoint type (EDGE/REGIONAL/PRIVATE), integration type, authorization
   model. Blocks deployment (PREREQUISITES_MISSING) on missing fields or
   incompatible combinations.
2. API type selection — REST (v1) vs HTTP (v2) based on feature
   requirements (usage plans, mapping templates, resource policies →
   REST; simple Lambda proxy with JWT → HTTP).
3. Resource/method model — path segments as resources, verbs as methods.
   Flags ANY + NONE auth as a security risk.
4. Integration types — AWS_PROXY (Lambda proxy), AWS (direct service),
   HTTP, HTTP_PROXY, MOCK. Configures Lambda `add-permission` for the
   API Gateway principal.
5. Authorization — AWS_IAM (sigv4), COGNITO_USER_POOLS (JWT), CUSTOM
   (Lambda authorizer, request or token). NEVER NONE for sensitive data.
6. Usage plans + API keys — per-consumer throttling (rate + burst) and
   quotas. Verifies apiKeyRequired on methods that need plan enforcement.
7. Stage throttling — account-level default (10K rps shared) and
   per-method overrides.
8. WAFv2 Web ACL — REGIONAL scope for REST APIs, CommonRuleSet +
   rate-based rules.
9. VPC Link — for NLB-backed private integrations. Verifies NLB target
   (not ALB direct).
10. Mapping templates — Velocity (VTL) for request/response transform
    (REST API only).
11. Canary deployments — percentage-based traffic shifting for safe
    releases.
12. Access logging — JSON format with `$context` variables to CloudWatch.
13. Custom domain names — ACM cert + base path mapping.
14. Deployment discipline — `create-deployment` as the final step
    (without it, changes are not live).

Emits a deterministic deployment plan per API:

```text
API_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Type / Endpoint / Resources / Integration / Authorization /
  Usage plan / WAF / Custom domain / Logging / Canary
CHECKLIST:
  [x] API type selected based on feature requirements
  [x] Resources and methods defined
  [x] Integration type configured
  [x] Authorization type set per method (NOT NONE for sensitive)
  [x] Usage plan with API keys for per-consumer throttling
  ...
FINDINGS:
  - [INFO] Cost estimate
  - [WARN] Account-level default throttle shared across all APIs
DEPLOY_COMMANDS:
  <ordered list of aws apigateway / apigatewayv2 commands>
```

## When to invoke

Provide a deployment spec and ask any of:

- "create a REST API with Lambda proxy"
- "provision an API Gateway with Cognito auth"
- "set up usage plans for per-consumer rate limiting"
- "deploy a VPC Link to my NLB"
- "configure canary deployments for my API"
- "map a custom domain to my API"
- "choose between REST and HTTP API"

A bare resource list + integration + "deploy REST API" also routes
here via the orchestrator.

## Inputs

- **Required:** api_type (REST or HTTP), endpoint_type (EDGE / REGIONAL
  / PRIVATE), integration_type (AWS_PROXY / AWS / HTTP / HTTP_PROXY /
  MOCK), authorization (AWS_IAM / COGNITO_USER_POOLS / CUSTOM / NONE),
  resource_method_layout (paths and verbs).
- **Optional:** usage_plan (rate/burst/quota), api_keys, waf_association,
  vpc_link_target_arn, mapping_templates, canary_percent,
  access_log_group, custom_domain, acm_certificate_arn.

## Outputs

- One VERDICT block per API (READY_TO_DEPLOY or PREREQUISITES_MISSING).
- ARCHITECTURE summary with type/endpoint/resources/auth/WAF/domain.
- CHECKLIST with all 14 deployment dimensions validated.
- FINDINGS with cost estimates and shared-throttle warnings.
- DEPLOY_COMMANDS with ordered `aws apigateway` and `aws apigatewayv2`
  commands (create-deployment last).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 1 Deploy specialist for API Gateway REST/HTTP APIs).
- `/aws:audit-apigateway-resource-policy` for post-deployment security
  auditing (public methods, cross-account exposure, usage plan coverage).
- `/aws:audit-wafv2-web-acl` for rule-level WAF analysis.
