# Advanced patterns - API Gateway HTTP API Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset — three facts that differentiate HTTP API (v2)

Three facts make HTTP API (v2) provisioning different from REST API
(v1):

- **Routes are flat `(method, path)` pairs, not a resource tree.** A
  route is `$default`, `ANY /{proxy+}`, `GET /users`, or `POST
  /orders`. No resources, no methods on resources, no nested hierarchy.
  The greedy `{proxy+}` catches every sub-path — combined with `ANY`
  it is the catch-all that makes exposure mistakes trivial.

- **Integrations are typed targets, not mapping-template contracts.**
  `AWS_PROXY` (Lambda proxy) is the default, but HTTP API also exposes
  `HTTP_PROXY`, `HTTP`, and direct AWS-service integrations including
  `STEP_FUNCTION` (`START_EXECUTION` / `START_SYNC_EXECUTION`), `SQS`
  (`SendMessage`), and `KINESIS` (`PutRecord` / `PutRecords`). These
  run **without a Lambda in the path**, lowering latency and cost —
  but the request/response shape is fixed by API Gateway.

- **JWT is the only user-facing authorizer; CORS and auto-deploy are
  first-class.** HTTP API supports `JWT` (OpenID Connect / Cognito
  issuer) and `AWS_IAM`. There is no `COGNITO_USER_POOLS` type and no
  Lambda authorizer — JWT is the user-facing contract. CORS is set at
  the API level. Stages default to `auto-deploy: true`, so every route
  change is live within seconds — there is no `create-deployment` step.

## Expert heuristic — $default stage race with Infrastructure-as-Code

When deploying HTTP API via CloudFormation, CDK, SAM, or Terraform, a
common failure is the `$default` auto-deploy racing the IaC engine's
`AWS::ApiGatewayV2::Deployment` resource. The symptom is drift: the
deployment resource reports CREATE_COMPLETE, but `$default` already
served traffic using the live config seconds earlier.

**Resolution heuristics:**
- Use **one** of: `AWS::ApiGatewayV2::Deployment` + pinned stage, OR
  `auto-deploy: true` with no deployment resource. Mixing both causes
  drift.
- For event-driven pipelines (CodePipeline Source + Build + Deploy),
  set stage `auto-deploy: true` and let CloudFormation manage only
  `::Route`, `::Integration`, `::Authorizer` — skip `::Deployment`.
- For audit-controlled environments, pin the stage and emit
  `::Deployment` with explicit `DependsOn` on every route and
  integration.

A baseline model trained on REST API assumes `create-deployment` is
mandatory. On HTTP API it is **optional and frequently harmful** when
`auto-deploy` is also enabled.

## Expert heuristic — greedy {proxy+} route precedence and the ANY trap

HTTP API route matching uses **most-specific match**, but `ANY` matches
every method including `OPTIONS`. Combined with `{proxy+}` it becomes a
catch-all that defeats narrower routes.

```text
GET /users/me                → exact match, wins over ANY /{proxy+}
ANY /{proxy+}                → catches everything else, ALL methods
ANY /users/{proxy+}          → narrower greedy under /users
$default                     → only when no route matches at all
```

**The ANY trap:** an `ANY /{proxy+}` route with `authorizationType:
NONE` exposes every sub-path on every method (GET, POST, PUT, PATCH,
DELETE, HEAD, OPTIONS). Operators add it for "a single Lambda handles
everything" and forget it includes DELETE. Always bind a JWT authorizer
to ANY routes, or split the greedy into explicit verbs. A baseline
model often suggests `ANY /{proxy+}` as the default route because it
minimizes route count. The secure pattern is the opposite: explicit
verbs, explicit authorizer per route.

## Edge-case handling

- **$default stage 404 after pinning.** A pinned stage
  (`auto-deploy=false`) without a current deployment ID serves 404 for
  every route. Always emit `create-deployment` before pinning.

- **JWT issuer trailing slash.** Cognito issuer URLs MUST end with `/`.
  A missing slash returns "invalid JWT configuration". Third-party OIDC
  providers may or may not require the trailing slash — match the
  OpenID configuration's `issuer` field exactly.

- **Audience mismatch on third-party OIDC.** Cognito uses `client_id`,
  which API Gateway recognizes. Other OIDC providers (Auth0, Okta) emit
  `aud` — the audience list MUST contain the exact `aud` value.

- **CORS `allowCredentials=true` with wildcard origin.** Hard AWS
  rejection — `allowOrigins` must enumerate explicit origins.

- **VPC link to ALB.** ALB is not a valid VPC link target. Front the
  ALB with an NLB, or use HTTP integration with the ALB DNS (which
  exposes the ALB to internet egress).

- **Direct SQS / Kinesis integration role.** The `credentials-arn` role
  must trust `apigateway.amazonaws.com` and have a policy scoped to the
  exact queue or stream ARN. A wildcard (`sqs:*`) creates a privilege
  escalation path if the API is exposed publicly.

## Pre-flight safety checks (run before any deployment CLI)

- **MANDATORY CONFIRMATION GATE.** Before changes go live (auto-deploy
  is on by default!), the deployer MUST emit:
  `CONFIRM: HTTP API <name> has auto-deploy enabled on stage '$default'.
  Any route / integration / authorizer change goes live within seconds.
  Proceed? (yes/no)`
- **Authorizer verification.** List every route; verify `NONE` auth
  appears ONLY on intentionally public routes (e.g., `/health`). The
  catch-all `ANY /{proxy+}` MUST have an authorizer bound.
- **JWT issuer reachability.** Verify
  `<issuer>/.well-known/openid-configuration` returns 200 with a JWKS
  URI. A non-reachable issuer breaks every authorized route.
- **CORS verification.** `allowOrigins` explicit (no `*` with
  credentials), `Authorization` in `allowHeaders` for JWT routes,
  `OPTIONS` in `allowMethods`.
- **Custom domain ACM cert.** Must be in the API's region (REGIONAL).
  HTTP API does not support EDGE custom domains.
- **Cost estimate.** HTTP API $1.00/M requests; WAF $5/ACL/month +
  $0.60/M requests; Cognito $0.0055/MAU; Lambda $0.20/M invocations +
  GB-second; Step Functions Express $1.00/M invocations + GB-second.

## Recent AWS features (2024-2026)

- **Step Functions direct integration (HTTP API):** HTTP APIs now
  integrate natively with Step Functions (`START_EXECUTION` for
  Standard, `START_SYNC_EXECUTION` for Express) without a Lambda in
  the path. Useful for synchronous workflow APIs (5s ceiling).

- **HTTP API private integrations via VPC Lattice:** HTTP APIs can
  route to VPC Lattice services as private integrations, expanding
  beyond NLB VPC link targets. Lattice auth policies may not appear in
  standard VPC security group audits — check separately.

- **Private integrations with VPC link improvements:** VPC link
  creation supports multiple security groups and subnet IDs directly
  via `create-vpc-link`, removing the need for a separate
  NLB-per-AZ configuration in many cases.

- **HTTP API mTLS:** HTTP APIs support mutual TLS via custom domain
  names. Use for B2B APIs with strict client certificate requirements.

- **OpenAPI 3.1 import + auto-deploy metrics + CORS subdomain
  wildcards:** OpenAPI 3.1 import now carries JWT authorizer and
  direct-integration subtypes; CloudWatch exposes
  `AutoDeployStageChanges` for drift detection; `cors-configuration`
  accepts up to 100 origins and `https://*.example.com` subdomain
  wildcards for tenant apps.
