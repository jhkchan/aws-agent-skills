---
description: Provision a production-grade AWS App Mesh service mesh with virtual nodes, weighted routes, virtual gateways, mTLS, circuit breaking, and Envoy sidecar injection.
nl_triggers:
  - "create App Mesh"
  - "deploy service mesh"
  - "App Mesh virtual node"
  - "App Mesh virtual router"
  - "App Mesh weighted routing"
  - "App Mesh canary deployment"
  - "App Mesh blue/green"
  - "App Mesh virtual gateway"
  - "App Mesh ingress"
  - "App Mesh mutual TLS"
  - "App Mesh mTLS"
  - "App Mesh retry policy"
  - "App Mesh timeout policy"
  - "App Mesh circuit breaker"
  - "Envoy sidecar injection"
  - "App Mesh Cloud Map"
  - "App Mesh Controller EKS"
  - "App Mesh Gateway Controller"
routes_to: appmesh-deployer
---

# /aws:deploy-appmesh

Activate the `appmesh-deployer` skill and produce a deployment plan
for a production-grade App Mesh service mesh with secure defaults.

## What it does

Reads a deployment specification (mesh name, egress filter, virtual
nodes, virtual routers, weighted routes, virtual gateway, mTLS,
circuit breaking, sidecar injection) and produces an ordered
deployment plan with:

1. Pre-flight specification gate — validates mesh name uniqueness,
   Cloud Map namespace existence, ACM cert region/status, ACM
   Private CA status (for mTLS), EKS namespace labeling. Blocks
   deployment (PREREQUISITES_MISSING) on missing fields or invalid
   mTLS configuration.
2. Mesh creation — `egress_filter: DROP_ALL` (production default)
   or `ALLOW_ALL` (with explicit WARN finding).
3. Virtual nodes — Cloud Map service discovery, listener with
   protocol + port + health check, optional backends (virtual
   services), optional logging.
4. Virtual routers — protocol-matched listener; one router per
   service.
5. Routes — HTTP/gRPC/TCP match; weighted targets summing to 100
   (canary) or 100/0 (blue/green); retry policy (HTTP/gRPC only);
   timeout policy (`requestTimeout` + `idleTimeout`).
6. Virtual gateway — listener with ACM cert (for HTTPS), gateway
   routes weighting to virtual services. ALB → gateway target
   group → gateway Envoy pods → mesh members.
7. mTLS — STRICT or PERMISSIVE mode via SDS; ACM Private CA or
   self-signed cert chain; listener enforces client cert validation.
8. Circuit breaking — connection pool (maxConnections,
   maxPendingRequests, maxRequests, maxRetries) + outlier detection
   (maxServerErrors, interval, baseEjectionDuration,
   maxEjectionPercent).
9. Sidecar injection — EKS: App Mesh Controller + namespace label;
   ECS: Envoy container in task definition; EC2: Envoy binary +
   APPMESH_RESOURCE_ARN env var.
10. App Mesh Gateway Controller for EKS — CRD-based gateway route
    reconciliation (alternative to direct CLI; pick one per mesh).

Emits a deterministic deployment plan per mesh:

```text
MESH_SPEC: <mesh-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Mesh / Egress / Virtual nodes / Routers / Routes / Gateway / mTLS / Circuit breaking / Sidecar
CHECKLIST:
  [x] Mesh egress filter DROP_ALL
  [x] Cloud Map namespace exists
  [x] Virtual nodes reference existing Cloud Map services
  [x] Route weights sum to 100 (canary) or 100/0 (blue/green)
  [x] Retry policy set for HTTP/gRPC routes
  [x] Timeout policy per_request_timeout + idle_timeout both set
  ...
FINDINGS:
  - [INFO] Canary 90/10 — monitor 5xx rate before shifting to 100/0
  - [WARN] Egress ALLOW_ALL — permissive posture
DEPLOY_COMMANDS:
  <ordered list of aws appmesh create-* commands>
```

## When to invoke

Provide a deployment spec and ask any of:

- "deploy an App Mesh with weighted routing"
- "create virtual nodes for checkout v1 and v2"
- "configure mTLS via ACM Private CA"
- "build a virtual gateway for ALB ingress"
- "configure circuit breaking on the checkout listener"
- "enable App Mesh sidecar injection on EKS namespace prod"

A bare mesh name + "deploy App Mesh" also routes here via the
orchestrator.

## Inputs

- **Required:** mesh name, egress filter (DROP_ALL | ALLOW_ALL), at
  least one virtual node with service discovery (Cloud Map or DNS),
  at least one virtual router with a route.
- **Optional:** virtual gateway (listener + ACM cert), gateway
  routes, mTLS (mode + CA ARN + SDS configuration), circuit
  breaking (connection pool + outlier detection), retry policy,
  timeout policy, sidecar injection target (EKS namespace, ECS task
  definition, EC2 binary), App Mesh Gateway Controller CRDs.

## Outputs

- One VERDICT block per mesh (READY_TO_DEPLOY or
  PREREQUISITES_MISSING).
- ARCHITECTURE summary with mesh / egress / virtual nodes / routers
  / routes / gateway / mTLS / circuit breaking / sidecar layout.
- CHECKLIST with all 10 deployment dimensions validated.
- FINDINGS with cost / resilience / security-posture warnings (e.g.,
  ALLOW_ALL egress WARN, no circuit breaking WARN, no mTLS INFO).
- DEPLOY_COMMANDS with ordered `aws appmesh create-*` commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 1 Deploy specialist for App Mesh service mesh).
- `/aws:deploy-vpc-network` for the underlying VPC + subnets the
  mesh members run in.
- `/aws:deploy-alb` for the ALB in front of the virtual gateway.
- `/aws:deploy-ecs-fargate` for ECS task definitions that include
  the Envoy sidecar.
