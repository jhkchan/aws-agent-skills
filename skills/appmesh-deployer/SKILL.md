---
name: appmesh-deployer
description: >-
  Provisions production-grade AWS App Mesh service meshes — mesh
  with egress filter (DROP_ALL vs ALLOW_ALL), virtual nodes with
  Cloud Map or DNS service discovery, virtual routers with weighted
  routes (HTTP / TCP / gRPC), retry and timeout policies, virtual
  gateways for ingress (ALB/NLB → gateway → mesh), mutual TLS via
  ACM Private CA and SDS, circuit breaking (connection pool +
  outlier detection), Envoy sidecar injection (EKS App Mesh
  Controller, ECS task, EC2 binary), and latest features (App Mesh
  Gateway Controller for EKS via CRDs). Runs pre-checks (Cloud Map
  namespace exists, ACM Private CA ACTIVE, IAM appmesh:Create*
  granted, EKS namespace labeled) and emits the exact appmesh
  create-mesh / create-virtual-node / create-route /
  create-virtual-gateway CLI behind a CONFIRM gate. Emits a
  verdict (READY_TO_DEPLOY | PREREQUISITES_MISSING). Use when
  provisioning a mesh, configuring canary routing,
  exposing services via a virtual gateway, hardening east-west
  with mTLS, or adopting the Gateway Controller.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline architecture
  planning. Live deployment uses aws appmesh create-mesh,
  create-virtual-node, create-virtual-router, create-route,
  create-virtual-gateway, create-gateway-route,
  create-virtual-service, describe-mesh, list-meshes,
  list-virtual-nodes, list-virtual-routers, list-routes,
  servicediscovery create-service, create-http-namespace,
  acm-pca create-certificate-authority (AWS CLI v2, SSO or key-based
  credentials). For EKS, also requires kubectl and the App Mesh
  Controller custom resource definitions.
keywords:
  - AWS App Mesh
  - service mesh
  - Envoy
  - virtual node
  - virtual router
  - virtual service
  - virtual gateway
  - gateway route
  - weighted routing
  - blue/green
  - canary
  - http route
  - tcp route
  - grpc route
  - retry policy
  - timeout policy
  - circuit breaking
  - outlier detection
  - connection pool
  - mutual TLS
  - mTLS
  - ACM Private CA
  - Cloud Map
  - service discovery
  - sidecar injection
  - egress filter
  - App Mesh Controller
  - EKS
  - App Mesh Gateway Controller
  - ingress
tags: [appmesh, networking, deploy, service-mesh, envoy, weighted-routing, virtual-gateway, mtls, cloud-map, circuit-breaking, eks, grpc]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Provisioning a new App Mesh service mesh, configuring virtual
    nodes with service discovery, authoring virtual routers with
    weighted/canary/blue-green routes, exposing services outside the
    mesh via a virtual gateway, hardening east-west traffic with
    mutual TLS, designing retry/timeout/circuit-breaker policies, or
    adopting the App Mesh Gateway Controller for EKS.
  activation_triggers:
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
  invocation_schema: >-
    Input shape (one of): (a) a deployment specification including
    mesh name, egress filter, virtual nodes (with service discovery
    backend), virtual routers with routes (HTTP/TCP/gRPC match,
    weighted targets, retry/timeout), optional virtual gateway (with
    ingress listeners), optional mTLS configuration, and optional
    EKS namespace mapping; (b) a partial spec for interactive
    refinement (e.g., "App Mesh with weighted routing between two
    versions of the checkout service"); (c) an existing mesh name
    for architecture review against the well-architected checklist.
    Output shape: { MESH_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[],
    FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ {
    READY_TO_DEPLOY, PREREQUISITES_MISSING, ERROR }.
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

**Live-account pre-flight checks (skip if doing offline architecture plan):**
1. Verify IAM permissions for `appmesh:CreateMesh`,
   `CreateVirtualNode`, `CreateVirtualRouter`, `CreateRoute`,
   `CreateVirtualGateway`, `CreateGatewayRoute`,
   `CreateVirtualService`, and `servicediscovery:CreateService`.
2. Verify the Cloud Map namespace exists:
   `aws servicediscovery list-namespaces --output table`.
   Capture the namespace ID — virtual nodes reference it.
3. For mTLS, verify the ACM Private CA exists and is ACTIVE:
   `aws acm-pca list-certificate-authorities --output table`.
4. For virtual gateway, verify the ALB/NLB listener forwards to the
   gateway's target group (the gateway's Envoy pods).
5. For EKS sidecar injection, verify the App Mesh Controller is
   installed: `kubectl get pods -n appmesh-system`.
6. For EKS namespace injection, verify the namespace is labeled:
   `kubectl get namespace <ns> --show-labels` —
   `appmesh.k8s.aws/sidecarInjectorWebhook=enabled`.

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

- **Mesh name is region-scoped, not global.** The same mesh name can
  exist in `us-east-1` and `us-west-2` as independent meshes. Cross-
  region mesh federation is NOT a feature — use multi-mesh with
  Gateway-to-Gateway over Transit Gateway/VPC Peering.

- **`egress_filter: DROP_ALL` is the default but easily overridden.**
  The default `DROP_ALL` blocks egress to anything outside the mesh
  (databases, SaaS APIs, etc.) unless explicitly added as a backend
  virtual service. Operators hit this on day 1 and switch to
  `ALLOW_ALL` to "fix" it. Surface the choice explicitly.

- **Virtual node does NOT deploy Envoy.** The virtual node is a
  configuration object that maps to a Cloud Map service. Deploying
  Envoy is a separate step (EKS controller injection, ECS task
  definition, EC2 binary). This is the #1 confusion point.

- **Virtual gateway is a per-mesh resource, not per-node.** There
  is typically ONE virtual gateway per mesh for north-south ingress.
  It runs a dedicated Envoy deployment (gateway pods). The ALB
  forwards to the gateway's target group, NOT directly to the
  service pods.

- **Route weights are relative, not absolute.** A route with two
  targets weighted 90/10 sends 90% to target A. Weights must sum to
  100 for canary; for blue/green, weights are 100/0 then 0/100. The
  App Mesh controller and CLI auto-normalize but verify the sum.

- **mTLS uses SPIFFE, not raw certs.** App Mesh mTLS uses the SPIFFE
  (Secure Production Identity Framework for Everyone) framework
  with `sdS` (Secret Discovery Service). The cert chain must be
  issued by ACM Private CA or self-signed and provided via SDS. The
  Envoy sidecar negotiates the cert; the listener enforces client
  cert validation.

- **TCP routes have NO match criteria.** A TCP route simply forwards
  all traffic to weighted targets. There is no L7 routing for TCP —
  use HTTP or gRPC for path/header routing.

- **Retry policy applies to HTTP and gRPC only.** TCP routes do not
  support retries. For HTTP, retries on `gateway-error` (5xx) by
  default; configurable to `5xx`, `gateway-error`, `reset`,
  `connect-failure`, `refused-stream`, `retriable-status-codes`,
  `retriable-headers`.

- **Timeout policy has TWO fields: `per_request_timeout` (request
  RTT) and `idle_timeout` (connection idle).** Set both — long-
  running requests can hang the connection pool if
  `per_request_timeout` is unset.

- **Circuit breaking has two axes: connection pool and outlier
  detection.** Connection pool caps concurrent connections / pending
  requests; outlier detection ejects unhealthy endpoints from the
  load-balancing pool. Without both, a slow downstream can exhaust
  the connection pool and cascade.

- **Cloud Map service name MUST match the virtual node's
  `cloudMapServiceName`.** Mismatch = service discovery returns
  empty endpoints = 503 from Envoy.

- **App Mesh Gateway Controller for EKS (2024) reconciles gateway
  routes via CRDs.** The CRD `gatewayroutes.appmesh.k8s.aws` is
  reconciled by the controller; CLI changes are overwritten on next
  reconciliation. Pick one (CRD or CLI) per mesh; do NOT mix.

- **Envoy hot restart preserves connection state across restarts.**
  Sidecar upgrades (App Mesh controller version, Envoy version) do
  not drop active connections, but verify via canary before
  rolling to production.

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

After the deploy commands, run:
1. `describe-mesh --mesh-name <name>` returns the mesh with expected
   `egress_filter`.
2. `list-virtual-nodes --mesh-name <name>` returns all expected
   nodes.
3. `list-routes --mesh-name <name> --virtual-router-name <router>`
   returns routes with the expected weighted targets.
4. `describe-route` on a route returns the expected retry/timeout
   policy.
5. `list-virtual-gateways --mesh-name <name>` (if gateway) returns
   the gateway with expected listeners.
6. For EKS: `kubectl get pods -n <ns>` shows Envoy sidecar injected
   (2/2 containers in READY column).
7. For mTLS: `kubectl exec -it <pod> -c envoy -- curl -s localhost:9901/listeners`
   shows the listener with `tls_context` populated.

## Common patterns (boilerplate)

### Create a mesh with DROP_ALL egress (production default)

```bash
aws appmesh create-mesh \
  --mesh-name "prod-checkout-mesh" \
  --spec '{"egressFilter":{"type":"DROP_ALL"}}'
```

`DROP_ALL` blocks egress to anything outside the mesh unless added
as a backend virtual service.

### Create a virtual node with Cloud Map service discovery

```bash
aws appmesh create-virtual-node \
  --mesh-name "prod-checkout-mesh" \
  --virtual-node-name "checkout-service-v1" \
  --spec '{
    "serviceDiscovery": {
      "cloudMap": {
        "namespaceName": "prod-internal",
        "serviceName": "checkout-v1",
        "attributes": [{"key":"version","value":"v1"}]
      }
    },
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"},
      "healthCheck": {
        "protocol": "http",
        "path": "/health",
        "healthyThreshold": 2,
        "unhealthyThreshold": 2,
        "timeoutMillis": 2000,
        "intervalMillis": 5000
      }
    }],
    "backends": [{"virtualService": {"virtualServiceName": "inventory.prod-checkout-mesh.svc.cluster.local"}}],
    "logging": {"accessLog": {"file": {"path": "/dev/stdout"}}}
  }'
```

### Create a virtual router with HTTP routing

```bash
aws appmesh create-virtual-router \
  --mesh-name "prod-checkout-mesh" \
  --virtual-router-name "checkout-router" \
  --spec '{
    "listeners": [{"portMapping": {"port": 8080, "protocol": "http"}}]
  }'
```

### Create a weighted route (canary: 90/10)

```bash
aws appmesh create-route \
  --mesh-name "prod-checkout-mesh" \
  --virtual-router-name "checkout-router" \
  --route-name "checkout-canary" \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/"},
      "action": {
        "weightedTargets": [
          {"virtualNode": "checkout-service-v1", "weight": 90},
          {"virtualNode": "checkout-service-v2", "weight": 10}
        ]
      },
      "retryPolicy": {
        "httpRetryEvents": ["gateway-error", "5xx"],
        "maxRetries": 3,
        "perRetryTimeoutMillis": 2000
      },
      "timeout": {
        "requestTimeoutMillis": 5000,
        "idleTimeoutMillis": 300000
      }
    }
  }'
```

For blue/green: swap weights to 100/0 (v1 full), then 0/100 (v2
full) over the deployment window.

### Create a virtual gateway for ingress

```bash
aws appmesh create-virtual-gateway \
  --mesh-name "prod-checkout-mesh" \
  --virtual-gateway-name "ingress-gateway" \
  --spec '{
    "listeners": [{
      "portMapping": {"port": 8443, "protocol": "http"},
      "tls": {
        "certificate": {"acm": {"certificateArn": "arn:aws:acm:us-east-1:111111111111:certificate/abc123"}},
        "mode": "PERMISSIVE"
      }
    }]
  }'

aws appmesh create-gateway-route \
  --mesh-name "prod-checkout-mesh" \
  --virtual-gateway-name "ingress-gateway" \
  --gateway-route-name "checkout-ingress" \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/checkout"},
      "action": {
        "target": {"virtualService": {"virtualServiceName": "checkout.prod-checkout-mesh.svc.cluster.local"}}
      }
    }
  }'
```

### Enable mutual TLS on a listener

```bash
aws appmesh update-virtual-node \
  --mesh-name "prod-checkout-mesh" \
  --virtual-node-name "checkout-service-v1" \
  --spec '{
    "serviceDiscovery": {"cloudMap": {"namespaceName": "prod-internal", "serviceName": "checkout-v1"}},
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"},
      "tls": {
        "certificate": {"sds": {"secretName": "checkout-cert"}},
        "mode": "STRICT",
        "validation": {
          "trust": {"sds": {"secretName": "checkout-ca-bundle"}}
        }
      }
    }]
  }'
```

`mode: STRICT` rejects clients without a valid cert; `PERMISSIVE`
allows both mTLS and plaintext during migration. SDS (Secret
Discovery Service) is the recommended cert distribution mechanism.

### Configure circuit breaking (connection pool + outlier detection)

```bash
aws appmesh update-virtual-node \
  --mesh-name "prod-checkout-mesh" \
  --virtual-node-name "checkout-service-v1" \
  --spec '{
    "serviceDiscovery": {"cloudMap": {"namespaceName": "prod-internal", "serviceName": "checkout-v1"}},
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"},
      "connectionPool": {
        "http": {"maxConnections": 100, "maxPendingRequests": 50, "maxRequests": 200, "maxRetries": 3}
      },
      "outlierDetection": {
        "maxServerErrors": 5,
        "intervalMillis": 10000,
        "baseEjectionDurationMillis": 30000,
        "maxEjectionPercent": 50
      }
    }]
  }'
```

### Enable Envoy sidecar injection on EKS namespace

```bash
# Install App Mesh Controller (one-time)
helm repo add eks https://aws.github.io/eks-charts
helm install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system --create-namespace

# Label the namespace for sidecar injection
kubectl label namespace prod appmesh.k8s.aws/sidecarInjectorWebhook=enabled

# Annotate pods with mesh + virtual node references
kubectl annotate pod checkout-v1-xyz \
  appmesh.k8s.aws/meshName=prod-checkout-mesh \
  appmesh.k8s.aws/virtualNode=checkout-service-v1
```

### Use App Mesh Gateway Controller CRD for EKS

```bash
# GatewayRoute CRD (reconciled by controller)
cat <<EOF | kubectl apply -f -
apiVersion: appmesh.k8s.aws/v1beta2
kind: GatewayRoute
metadata:
  name: checkout-ingress
  namespace: prod
spec:
  httpRoute:
    match:
      prefix: "/checkout"
    action:
      target:
        virtualService:
          virtualServiceRef:
            name: checkout
EOF
```

CRD-managed resources override CLI changes; pick one mechanism per
mesh.

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

```text
MESH_SPEC: prod-secure-mesh
VERDICT: PREREQUISITES_MISSING
ARCHITECTURE: (incomplete — pre-checks failed)
CHECKLIST:
  - [FAIL] ACM Private CA not found in account 111111111111
FINDINGS:
  - [BLOCKER] mTLS requires an ACM Private CA in ACTIVE status. List
    current CAs: aws acm-pca list-certificate-authorities. Create a
    new CA: aws acm-pca create-certificate-authority --certificate-authority-configuration ...
    Wait for Status: ACTIVE before referencing it in the listener
    tls block.
  - [BLOCKER] Cloud Map namespace secure-internal not found. Create:
    aws servicediscovery create-private-dns-namespace --name secure-internal --vpc vpc-abc123
    Wait for Status: ACTIVE before referencing in virtual nodes.
DEPLOY_COMMANDS: (none — pre-checks failed)
```

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

- **App Mesh Gateway Controller for EKS (2024)**: CRD-based
  reconciliation of gateway routes, virtual nodes, virtual routers,
  virtual services, and virtual gateways. Replaces direct CLI
  management for EKS-native workflows; pick one mechanism per mesh.
- **mTLS via SDS (Secret Discovery Service)** (2023, refined 2024):
  Envoy negotiates certs via SDS instead of static file mounts;
  supports ACM Private CA and self-signed; rolling cert updates
  without Envoy restart.
- **Circuit breaking improvements**: connection pool and outlier
  detection on virtual node listeners (per-listener granularity);
  ejection duration, max-ejection-percent configurable.
- **gRPC route enhancements**: `serviceName` and `methodName` match;
  retry on gRPC status codes.
- **App Mesh timeout policy**: per-route `requestTimeoutMillis` and
  `idleTimeoutMillis` (separate from retry `perRetryTimeoutMillis`).
- **Multi-cluster mesh via Gateway-to-Gateway**: limited support
  via virtual gateway peering over Transit Gateway; not a true
  federated mesh.
- **Envoy version upgrades**: App Mesh controller pins Envoy
  versions; verify before controller upgrade.

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
