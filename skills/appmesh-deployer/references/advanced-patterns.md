# App Mesh Advanced Patterns and Expert Knowledge (load on demand)

Step 0 expert-knowledge deep dives and recent AWS features, moved verbatim from SKILL.md.


## Step 0: Expert knowledge — non-obvious App Mesh behaviors


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
