---
name: appmesh-deployer
description: Provisions production-grade AWS App Mesh service meshes — mesh with egress filter (DROP_ALL vs ALLOW_ALL), virtual nodes with Cloud Map or DNS service discovery, virtual routers with weighted routes (HTTP / TCP / gRPC), retry and timeout policies, virtual gateways for ingress (ALB/NLB → gateway → mesh), mutual TLS via ACM Private CA and SDS, circuit breaking (connection pool + outlier detection), Envoy sidecar injection (EKS App Mesh Controller, ECS task, EC2 binary), and latest features (App Mesh Gateway Controller for EKS via CRDs). Runs pre-checks (Cloud Map namespace exists, ACM Private CA ACTIVE, IAM appmesh:Create* granted, EKS namespace labeled) and emits the exact appmesh create-mesh / create-virtual-node / create-route / create-virtual-gateway CLI behind a CONFIRM gate. Emits a verdict (READY_TO_DEPLOY | PREREQUISITES_MISSING). Use when provisioning a mesh, configuring canary routing, exposing services via a virtual gateway, hardening east-west with mTLS, or adopting the Gateway Controller.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline architecture planning. Live deployment uses aws appmesh create-mesh, create-virtual-node, create-virtual-router, create-route, create-virtual-gateway, create-gateway-route, create-virtual-service, describe-mesh, list-meshes, list-virtual-nodes, list-virtual-routers, list-routes, servicediscovery create-service, create-http-namespace, acm-pca create-certificate-authority (AWS CLI...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning a new App Mesh service mesh, configuring virtual nodes with service discovery, authoring virtual routers with weighted/canary/blue-green routes, exposing services outside the mesh via a virtual gateway, hardening east-west traffic with mutual TLS, designing retry/timeout/circuit-breaker policies, or adopting the App Mesh Gateway Controller for EKS.
  activation_triggers: create App Mesh, deploy service mesh, App Mesh virtual node, App Mesh virtual router, App Mesh weighted routing, App Mesh canary deployment, App Mesh blue/green, App Mesh virtual gateway, App Mesh ingress, App Mesh mutual TLS, App Mesh mTLS, App Mesh retry policy, App Mesh timeout policy, App Mesh circuit breaker, Envoy sidecar injection, App Mesh Cloud Map, App Mesh Controller EKS, App Mesh Gateway Controller
  invocation_schema: 'Input shape (one of): (a) a deployment specification including mesh name, egress filter, virtual nodes (with service discovery backend), virtual routers with routes (HTTP/TCP/gRPC match, weighted targets, retry/timeout), optional virtual gateway (with ingress listeners), optional mTLS configuration, and optional EKS namespace mapping; (b) a partial spec for interactive refinement (e.g., "App Mesh with weighted routing between two versions of the checkout service"); (c) an existing mesh name for architecture review against the well-architected checklist. Output shape: { MESH_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING, ERROR }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS App Mesh, service mesh, Envoy, virtual node, virtual router, virtual service, virtual gateway, gateway route, weighted routing, blue/green, canary, http route, tcp route, grpc route, retry policy, timeout policy, circuit breaking, outlier detection, connection pool, mutual TLS, mTLS, ACM Private CA, Cloud Map, service discovery, sidecar injection, egress filter, App Mesh Controller, EKS, App Mesh Gateway Controller, ingress
  tags: appmesh, networking, deploy, service-mesh, envoy, weighted-routing, virtual-gateway, mtls, cloud-map, circuit-breaking, eks, grpc
---

# App Mesh Deployer

## What this skill does

Provisions production-grade App Mesh service meshes with secure
defaults — mesh + egress filter, virtual nodes with service
discovery, virtual routers with weighted routes and retry/timeout
policies, virtual gateways for ingress, mTLS for east-west traffic,
and Envoy sidecar injection via Cloud Map. Runs deterministic
pre-checks (Cloud Map namespace exists, mTLS ACM Private CA issued,
IAM `appmesh:Create*` granted, EKS namespace labeled for injection)
and emits the exact `appmesh create-*` CLI sequence behind a
CONFIRM gate.

## Mindset

**One-line takeaway:** an App Mesh service mesh is not "Envoy
sidecars for free" — it is a **per-mesh policy boundary** where the
egress filter, mTLS posture, and route-level retry/timeout policies
determine the blast radius of a downstream failure. Weighted routing
is the most visible feature; **egress control, mTLS, and circuit
breaking** determine resilience.

Three facts make App Mesh provisioning different from "roll out
Envoy":

- **The mesh has an egress filter; the default is DROP_ALL.**
  `egress_filter: DROP_ALL` blocks all egress traffic from mesh
  members to non-mesh destinations unless explicitly added as a
  virtual service backend. Operators frequently set `ALLOW_ALL` to
  "make it work" then forget to tighten — exposing a permissive
  egress posture. Production meshes should use DROP_ALL with
  explicit virtual services for external dependencies.

- **Virtual nodes are NOT workloads; they are service-discovery
  endpoints.** A virtual node binds to a Cloud Map service or DNS
  hostname, plus a listener port/protocol. It does NOT deploy a
  workload — the workload is the EC2/ECS/EKS task running the Envoy
  sidecar. Forgetting this is the #1 confusion: operators create
  virtual nodes and expect traffic to flow without deploying Envoy.

- **Virtual gateway is the only ingress path from outside the mesh.**
  ALB → virtual gateway → mesh-internal services. ALB → virtual node
  directly does NOT go through Envoy and bypasses all mesh policies
  (retries, timeouts, mTLS). For public ingress that needs mesh
  policies, use a virtual gateway.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Deployment checklist + pre-flight spec gate | Before any deployment |
| **§ Mindset** | Egress filter, virtual node != workload, virtual gateway | Understanding the model |
| **§ Pre-flight** | Cloud Map / ACM / EKS namespace gate | Before producing architecture |
| **§ Process** | Step-by-step deployment: mesh, nodes, routers, routes, gateway, mTLS, circuit breaking, sidecar | When building the deploy plan |
| **§ Common patterns** | Boilerplate for mesh, canary route, virtual gateway, mTLS, circuit breaking, EKS injection | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS, DEPLOY_COMMANDS | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes | Review before risky operations |

## Quick reference — deployment checklist

| Dimension | Requirement | Step |
|---|---|---|
| Mesh name | Globally unique within the account+region | Step 1 |
| Egress filter | `DROP_ALL` (default, recommended) or `ALLOW_ALL` | Step 1 |
| Cloud Map namespace | HTTP or DNS namespace exists; virtual nodes reference a Cloud Map service | Step 2 |
| Service discovery | Virtual node specifies Cloud Map `serviceName` or DNS `hostName` | Step 2 |
| Virtual node listener | Protocol (http/tcp/grpc), port, optional mTLS | Step 3 |
| Virtual node backends | List of virtual services the node depends on | Step 3 |
| Virtual router | Protocol-matched to listener; listens on a port | Step 4 |
| Route match | HTTP `prefix`/`method`/`headers`, TCP no match, gRPC `serviceName` | Step 5 |
| Route weighted targets | Sum of weights = 100; targets are virtual nodes | Step 5 |
| Retry policy | HTTP retries on gateway errors; TCP no retry | Step 5 |
| Timeout policy | Per-route request timeout + idle timeout | Step 5 |
| Virtual gateway | Listens on a port; ALB/NLB in front | Step 6 |
| Gateway route | HTTP/gRPC match, weighted to virtual services | Step 6 |
| mTLS | ACM Private CA or self-signed; listener enforces | Step 7 |
| Circuit breaking | Connection pool + outlier detection on virtual node | Step 8 |
| Sidecar injection | EKS: App Mesh Controller + namespace label; ECS: Envoy container in task definition | Step 9 |
| App Mesh Gateway Controller | EKS CRD-based gateway route reconciliation | Step 10 |

## Pre-flight: deployment specification gate (run before architecture output)

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment** — proceeding with an invalid
spec produces a non-functional or insecure mesh.

Full live-account pre-flight command listing moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load it before running pre-flight checks against a live account.

| Attribute | Value | Effect on plan |
|---|---|---|
| Mesh name | Listed | MUST be unique within account+region |
| Egress filter | `DROP_ALL` | Production recommended; requires explicit virtual services for external deps |
| Egress filter | `ALLOW_ALL` | Permissive — surface as INFO/security finding |
| Cloud Map namespace | HTTP (`CreateHttpNamespace`) | Service discovery via API calls; no DNS |
| Cloud Map namespace | DNS (`CreatePrivateDnsNamespace` or `CreatePublicDnsNamespace`) | Service discovery via DNS; recommended |
| Service discovery | Cloud Map | Recommended — App Mesh integrates natively |
| Service discovery | DNS `hostName` | Static; for non-Cloud Map workloads |
| mTLS requirement | true | MUST have ACM Private CA or self-signed cert; listener enforces |
| Ingress | Virtual gateway | ALB/NLB in front; gateway route weighted to virtual services |
| Compute | EKS | App Mesh Controller + namespace label for sidecar injection |
| Compute | ECS | Envoy container in task definition; `APPMESH_RESOURCE_ARN` env var |
| Compute | EC2 | Envoy binary + `APPMESH_RESOURCE_ARN` env var |

**If the deployment spec is incomplete** (missing mesh name, no service
discovery, no virtual node listener, no route match), output:

```text
VERDICT: PREREQUISITES_MISSING
FINDINGS:
  - [BLOCKER] <missing field> required for deployment
```

Do NOT proceed to architecture output.

## Process — deployment planning (apply in order)

### Step 0: Expert knowledge — non-obvious App Mesh behaviors
Step 0 deep-dive detail moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it before producing the deployment plan or when mesh behavior seems non-obvious.

### Step 1: Pre-check gate — PREREQUISITES_MISSING if any check fails

Run ALL pre-checks. If ANY fails, verdict is PREREQUISITES_MISSING
with failures in FINDINGS. Do NOT emit DEPLOY_COMMANDS.

**For ALL deployments:**
1. Mesh name unique within account+region.
2. IAM role holds `appmesh:CreateMesh` and downstream create
   permissions.
3. Cloud Map namespace exists (or `servicediscovery:CreateNamespace`
   is in the plan).

**For virtual nodes:**
4. Cloud Map service name matches the virtual node's
   `cloudMapServiceName`.
5. Listener protocol + port specified (`http`/`tcp`/`grpc`, port
   1-65535).
6. For mTLS: ACM Private CA ARN exists and is ACTIVE.

**For routes:**
4. Virtual router exists and listens on a port.
5. Route match valid for protocol (HTTP prefix/method/headers, gRPC
   serviceName, TCP no match).
6. Weighted targets sum to 100 (canary) or 100/0 (blue/green).
7. Targets reference existing virtual nodes.
8. Retry policy `httpRetryPolicy` valid only for HTTP/gRPC.
9. Timeout policy `per_request_timeout` and `idle_timeout` both set
   (or explicitly default).

**For virtual gateway:**
4. Listener port and protocol specified.
5. ALB/NLB listener forwards to gateway target group (the gateway's
   Envoy pods).
6. Gateway route match valid for protocol.

**For mTLS:**
4. ACM Private CA ARN exists and `Status: ACTIVE`.
5. Listener `tls` block specifies `mode: STRICT` or `PERMISSIVE`.
6. SDS (Secret Discovery Service) backend configured on Envoy.

**For EKS sidecar injection:**
4. App Mesh Controller installed in `appmesh-system` namespace.
5. Target namespace labeled
   `appmesh.k8s.aws/sidecarInjectorWebhook=enabled`.
6. Pod annotations: `appmesh.k8s.aws/meshName`, `appmesh.k8s.aws/virtualNode`.

### Step 2: READY_TO_DEPLOY — emit deployment plan

Emit `VERDICT: READY_TO_DEPLOY` with the exact CLI sequence +
CONFIRM gate:
- Ordered `aws appmesh create-*` commands (mesh first, virtual nodes
  before routers, routers before routes, virtual gateway before
  gateway routes).
- Cloud Map service creation (if needed) before virtual nodes.
- EKS namespace labeling + controller installation notes.
- CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-mesh`, `create-virtual-node`, `create-virtual-router`,
  `create-route`, `create-virtual-gateway`, `create-gateway-route`,
  `create-virtual-service`, `update-route`, `delete-route`), emit
  CONFIRM prompt.
- Mesh changes are not atomic — a partial deploy (mesh created,
  virtual nodes failed) leaves the mesh in a partial state. Always
  emit the full ordered command list so the operator can resume.
- For weighted-route changes (canary, blue/green), snapshot the
  current route via `describe-route --output json` before update;
  there is no rollback, but the snapshot enables manual revert.

### Step 4: Post-verification — COMPLETED-equivalent check

Verification command listing moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load it after the CONFIRM gate executes to verify the deployment.

## Common patterns (boilerplate)

All boilerplate moved: mesh/node/router and sidecar/CRD examples to [references/worked-examples.md](references/worked-examples.md); weighted-route and circuit-breaking examples to [references/traffic-policy-and-resilience-guide.md](references/traffic-policy-and-resilience-guide.md); gateway and mTLS examples to [references/virtual-gateway-and-mtls-guide.md](references/virtual-gateway-and-mtls-guide.md).
Load the fitting reference when emitting DEPLOY_COMMANDS.

## Output format (per deployment)

```text
MESH_SPEC: <mesh-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Mesh: <name>, egress_filter: DROP_ALL
  Virtual nodes: <count>, with Cloud Map / DNS service discovery
  Virtual routers: <count>, with weighted routes
  Virtual gateway: <yes/no>, ALB listener port
  mTLS: <STRICT|PERMISSIVE|disabled>, CA: <ACM PCA ARN>
  Circuit breaking: <connection pool + outlier detection on/off>
  Sidecar: <EKS controller injection | ECS task definition | EC2 binary>
CHECKLIST:
  [x] Mesh egress filter DROP_ALL
  [x] Cloud Map namespace exists
  [x] Virtual nodes reference existing Cloud Map services
  [x] Route weights sum to 100 (canary) or 100/0 (blue/green)
  [x] Retry policy set for HTTP/gRPC routes
  [x] Timeout policy per_request_timeout + idle_timeout both set
  [x] Virtual gateway listener + ALB target group
  [x] mTLS ACM Private CA ACTIVE
  [x] Circuit breaking connection pool + outlier detection
  [x] EKS namespace labeled for sidecar injection
FINDINGS:
  - [INFO] Weighted route 90/10 — verify metrics before shifting to 100/0
  - [WARN] Egress ALLOW_ALL — permissive posture
DEPLOY_COMMANDS:
  1. <aws appmesh create-mesh ...>
  2. <aws servicediscovery create-service ...>
  3. <aws appmesh create-virtual-node ...>
  4. <aws appmesh create-virtual-router ...>
  5. <aws appmesh create-route ...>
  ...
```

### Worked example — weighted canary (READY_TO_DEPLOY)

```text
MESH_SPEC: prod-checkout-mesh
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Mesh: prod-checkout-mesh, egress_filter: DROP_ALL
  Virtual nodes: checkout-service-v1, checkout-service-v2
  Virtual router: checkout-router on port 8080
  Route: checkout-canary 90/10 (v1/v2)
  Retry: gateway-error, 5xx, maxRetries 3, perRetry 2s
  Timeout: request 5s, idle 300s
  mTLS: disabled (INFO — surface for east-west security review)
  Sidecar: EKS controller injection on namespace prod
CHECKLIST:
  [x] Mesh egress filter DROP_ALL
  [x] Cloud Map namespace prod-internal exists (ID: ns-abc123)
  [x] Virtual nodes reference cloudMap serviceName checkout-v1, checkout-v2
  [x] Route weights sum to 100 (90 + 10)
  [x] Retry policy set (gateway-error, 5xx, 3 retries, 2s perRetry)
  [x] Timeout policy request 5s, idle 300s
  [x] EKS namespace prod labeled appmesh.k8s.aws/sidecarInjectorWebhook=enabled
FINDINGS:
  - [INFO] Canary 10% — monitor 5xx rate for 30 min before shifting to 100/0
  - [INFO] No mTLS — east-west traffic is plaintext; consider ACM Private CA
  - [WARN] No circuit breaking configured — slow downstream can exhaust pool
DEPLOY_COMMANDS:
  1. aws appmesh create-mesh --mesh-name prod-checkout-mesh --spec '{"egressFilter":{"type":"DROP_ALL"}}'
  2. aws servicediscovery create-service --name checkout-v1 --namespace-id ns-abc123 --dns-config '{"NamespaceId":"ns-abc123","DnsConfig":{"RoutingPolicy":"WEIGHTED","DnsRecords":[{"Type":"A","TTL":60}]}}'
  3. aws appmesh create-virtual-node --mesh-name prod-checkout-mesh --virtual-node-name checkout-service-v1 --spec '<full spec>'
  4. aws appmesh create-virtual-node --mesh-name prod-checkout-mesh --virtual-node-name checkout-service-v2 --spec '<full spec>'
  5. aws appmesh create-virtual-router --mesh-name prod-checkout-mesh --virtual-router-name checkout-router --spec '{"listeners":[{"portMapping":{"port":8080,"protocol":"http"}}]}'
  6. aws appmesh create-route --mesh-name prod-checkout-mesh --virtual-router-name checkout-router --route-name checkout-canary --spec '<full canary spec>'
```

### Worked example — mTLS missing CA (PREREQUISITES_MISSING)

Full example moved to [references/worked-examples.md](references/worked-examples.md).
Load it when pre-checks fail and the verdict is PREREQUISITES_MISSING.

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
MESH_SPEC: <mesh-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Mesh / Egress / Virtual nodes / Routers / Routes / Gateway / mTLS / Circuit breaking / Sidecar
CHECKLIST:
  [x] <check description>
  [ ] <check description (not yet passed)>
FINDINGS:
  - [INFO | WARN | BLOCKER] <finding description>
DEPLOY_COMMANDS:
  <ordered list of aws appmesh create-* commands>
```

### FORBIDDEN output patterns

- NEVER start with conversational preamble ("Let me plan your mesh…") — the VERDICT block is the FIRST line, always. Use uppercase verdict values only (`READY_TO_DEPLOY`, `PREREQUISITES_MISSING`).
- NEVER omit the CHECKLIST — every dimension (egress, Cloud Map, virtual nodes, routes, retry, timeout, gateway, mTLS, circuit breaking, sidecar) must appear with `[x]` (passed) or `[ ]` (not passed) and a specific reason for each failure.
- NEVER propose `egress_filter: ALLOW_ALL` for production without flagging it as a WARN finding and surfacing DROP_ALL as the recommended posture.
- NEVER list a CLI command with placeholder flags in a READY_TO_DEPLOY plan — every flag must be populated with actual values from the input spec.
- NEVER mix CLI and CRD-based gateway route management on the same mesh — pick one mechanism per mesh (CRD via App Mesh Gateway Controller, or direct CLI) and state the choice in FINDINGS.

## Anti-Patterns — NEVER do these things

- NEVER set `egress_filter: ALLOW_ALL` for production meshes without an explicit WARN finding. DROP_ALL is the secure default; ALLOW_ALL permits mesh members to reach any destination (including malicious endpoints) without inspection.
- NEVER confuse virtual nodes with workloads. Virtual nodes are service-discovery mappings; Envoy sidecars must be deployed separately (EKS controller injection, ECS task definition, EC2 binary). A mesh with virtual nodes but no Envoy sidecars routes no traffic.
- NEVER route ALB traffic directly to mesh member pods expecting mesh policies. Mesh policies (retry, timeout, mTLS) apply only to traffic flowing through Envoy. For ingress with mesh policies, use a virtual gateway as the ALB target.
- NEVER update a weighted route without snapshotting via `describe-route --output json`. There is no rollback; the snapshot enables manual revert if the new weights produce errors.
- NEVER deploy mTLS in `STRICT` mode without first running `PERMISSIVE` mode to confirm cert distribution via SDS. A misconfigured SDS backend causes STRICT mTLS to reject all connections, producing a complete outage.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing CLI.
- **Snapshot before weighted-route update:** `describe-route --output
  json > /tmp/<route>-backup-$(date +%s).json` — there is no
  rollback; the snapshot enables manual revert.
- **Verify Cloud Map service health** before shifting weight —
  unhealthy endpoints in the Cloud Map service produce 503s under
  the new weights.
- **Canary before blue/green** — shift to 90/10 (or 99/1) and
  observe 5xx rate for 30 min before shifting to 100/0.
- **Test mTLS in PERMISSIVE first** — confirm cert distribution via
  SDS before enforcing STRICT mode.

## Expert heuristic: weighted routing strategy

```
CANARY (progressive)
   ├─ Low-risk change (config, copy, hotfix)
   │    └─ 95/5 -> 90/10 -> 50/50 -> 0/100
   │         • Observe 5xx rate at each stage for 15-30 min
   │         • Rollback to previous weights if 5xx > threshold
   ├─ High-risk change (new dependency, schema migration)
   │    └─ 99/1 -> 90/10 -> 50/50 -> 0/100
   │         • Internal-test traffic first (1%)
   │         • Observe for 60+ min at each stage
   │         • Pair with circuit breaking (outlier detection) to
   │           auto-eject unhealthy v2 endpoints
   ├─ Blue/Green (instant cutover)
   │    └─ 100/0 -> 0/100
   │         • Use for incompatible changes (API contract break)
   │         • Snapshot weights before cutover for manual revert
   │         • Cannot progressively observe — full blast
```

**Per-protocol routing semantics:**

| Protocol | Match criteria | Retry support | Notes |
|---|---|---|---|
| HTTP | `prefix`, `method`, `headers` (exact, prefix, regex) | gateway-error, 5xx, reset, connect-failure, refused-stream, retriable-status-codes, retriable-headers | Most flexible; default for REST services |
| gRPC | `serviceName`, `methodName` | cancelled, deadline-exceeded, internal, resource-exhausted, unavailable | Required for gRPC services; HTTP match does not work |
| TCP | None | None | Use only for non-L7 protocols (database connection pooling); no L7 routing |

**Circuit breaker thresholds (starting points):**

| Workload type | maxConnections | maxPendingRequests | maxRequests | maxRetries | outlier maxServerErrors | maxEjectionPercent |
|---|---|---|---|---|---|---|
| API frontend | 100 | 50 | 200 | 3 | 5 | 50 |
| API backend | 50 | 25 | 100 | 2 | 5 | 50 |
| Database proxy | 20 | 10 | 50 | 1 | 3 | 30 |
| Streaming / WebSocket | 1000 | n/a | n/a | 0 | 10 | 50 |

ALWAYS pair with the Cloud Map health check — outlier detection
supplements, not replaces, service-level health.

## Recent AWS features (2024-2026)

Feature detail moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when choosing CRD vs CLI management or planning controller/Envoy upgrades.

## Domain

AWS CloudOps / App Mesh Service Mesh Provisioning.

## AWS documentation

- **AWS App Mesh User Guide** — https://docs.aws.amazon.com/app-mesh/latest/userguide/what-is-app-mesh.html
- **Virtual Nodes** — https://docs.aws.amazon.com/app-mesh/latest/userguide/virtual_nodes.html
- **Virtual Routers and Routes** — https://docs.aws.amazon.com/app-mesh/latest/userguide/virtual_routers.html
- **Virtual Gateways** — https://docs.aws.amazon.com/app-mesh/latest/userguide/virtual_gateways.html
- **Mutual TLS** — https://docs.aws.amazon.com/app-mesh/latest/userguide/mutual-tls.html
- **Circuit Breaking** — https://docs.aws.amazon.com/app-mesh/latest/userguide/circuit-breaking.html
- **App Mesh and EKS** — https://docs.aws.amazon.com/app-mesh/latest/userguide/getting-started-eks.html
- **App Mesh Gateway Controller** — https://docs.aws.amazon.com/app-mesh/latest/userguide/gateway-controller.html
- **AWS App Mesh API Reference** — https://docs.aws.amazon.com/app-mesh/latest/APIReference/
- **AWS CLI appmesh reference** — https://docs.aws.amazon.com/cli/latest/reference/appmesh/

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked example (PREREQUISITES_MISSING) and common-pattern CLI boilerplate: mesh, virtual node, virtual router, EKS sidecar injection, Gateway Controller CRD
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight command listing and post-deployment verification commands (Step 4)
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert-knowledge deep dives and Recent AWS features (2024-2026)
- [references/traffic-policy-and-resilience-guide.md](references/traffic-policy-and-resilience-guide.md) — weighted canary route (with retry/timeout) and circuit-breaking CLI boilerplate
- [references/virtual-gateway-and-mtls-guide.md](references/virtual-gateway-and-mtls-guide.md) — virtual gateway ingress and mTLS listener CLI boilerplate
