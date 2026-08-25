---
name: appmesh-virtual-service-deployer
description: 'Provisions AWS App Mesh virtual service layer resources with production defaults: service mesh creation (egress filter DROP_ALL vs ALLOW_ALL), virtual nodes with DNS service discovery (hostname-based) vs Cloud Map service discovery (namespace-based, auto-registration), virtual services backed by virtual nodes or virtual routers, virtual routers with weighted route configuration (HTTP / TCP / gRPC routes for canary traffic shifting), timeout and retry policies (per-route and per-virtual-node), circuit breaker via connection pool limits and outlier detection, virtual gateway for north-south ingress (ALB/NLB → gateway → mesh), Envoy proxy injection (auto-inject on EKS via App Mesh mutating admission webhook, ECS sidecar registration, EC2 manual sidecar), xDS protocol (Envoy fetches. Triggers: create app mesh virtual service, app mesh virtual node, app mesh virtual router, weighted routing canary, app mesh envoy inject, app mesh mTLS, virtual gateway ingress, app mesh cloud map discovery, app mesh dns discovery.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with appmesh create-mesh, create-virtual-node, create-virtual-router, create-route, create-virtual-service, create-virtual-gateway, create-gateway-route (AWS CLI v2, SSO or key-based credentials). For EKS Envoy injection: kubectl and the App Mesh Controller with mutating webhook configuration. For Cloud Map: servicediscovery create-service, create-http-namespace. For mTLS:...'
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
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, appmesh, service-mesh, virtual-service, envoy, networking, deploy, cloudops, weighted-routing, canary, cloud-map, mtls, circuit-breaking
  dependencies: aws-orchestrator
  keywords: aws, app mesh, service mesh, virtual node, virtual service, virtual router, virtual gateway, weighted routing, canary deploy, traffic shifting, envoy proxy, envoy sidecar, auto inject, mutating webhook, xds protocol, cloud map, dns service discovery, service discovery, circuit breaker, outlier detection, connection pool, retry policy, timeout policy, mTLS, acm private ca, x-ray tracing, cloudwatch metrics, cloudops, deploy, networking
  when_to_use: Invoke when the user wants to create an App Mesh service mesh with virtual nodes, virtual services, and virtual routers, configure weighted routing for canary traffic shifting, set up a virtual gateway for north-south ingress, inject Envoy sidecars (auto-inject on EKS via webhook, ECS sidecar, or EC2 manual), enable mTLS via ACM Private CA, configure circuit breakers and outlier detection, or integrate CloudWatch metrics and X-Ray tracing. Do NOT invoke for AWS Cloud Map service discovery without App Mesh (use servicediscovery skills), Istio service mesh (different control plane), or AWS Gateway Load Balancer (different Layer 3/4 inspection service).
---

# App Mesh Virtual Service Deployer

An AWS CloudOps agent skill that provisions AWS App Mesh virtual
service layer resources with correct defaults. The skill walks the
operator through service mesh creation, virtual node service discovery
(DNS vs Cloud Map), virtual router weighted route configuration for
canary deployments, Envoy sidecar injection (auto-inject on EKS via
mutating webhook), virtual gateway ingress, mTLS via ACM Private CA,
circuit breaking, and observability (CloudWatch + X-Ray). It captures
the mesh topology decisions, explains why each default matters, and
emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

create app mesh virtual service, app mesh virtual node, app mesh
virtual router, weighted routing canary, app mesh envoy inject, app
mesh mTLS, virtual gateway ingress, app mesh cloud map discovery, app
mesh dns discovery.

## STRICT output contract

When this skill is invoked with an App Mesh virtual-service-
provisioning request (create a mesh, configure virtual nodes,
weighted routing, virtual gateway, Envoy injection, mTLS, circuit
breaking, or a partial configuration), the agent MUST respond with
the READY_TO_DEPLOY checklist defined in the "Output format" section
using the literal all-caps labels `APP_MESH:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the
checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-
based evals and downstream provisioning pipelines rely on; deviating
from the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Service mesh creation | Mesh + egress filter |
| Step 2 — Virtual nodes (DNS vs Cloud Map) | Service discovery decision |
| Step 3 — Virtual routers and weighted routes | Canary traffic shifting |
| Step 4 — Route policies (timeout, retry) | Resilience configuration |
| Step 5 — Circuit breaker and outlier detection | Fault isolation |
| Step 6 — Virtual services | Abstraction layer |
| Step 7 — Virtual gateway (north-south ingress) | External traffic entry |
| Step 8 — Envoy sidecar injection | Data plane provisioning |
| Step 9 — mTLS via ACM Private CA | East-west security |
| Step 10 — Observability (CloudWatch + X-Ray) | Monitoring and tracing |
| Step 11 — Mesh scope (namespace vs cluster) | EKS scoping |
| Step 12 — xDS protocol | Control plane communication |
| Step 13 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/service-discovery-and-routing.md | DNS vs Cloud Map + routing detail |
| references/envoy-and-mtls-guide.md | Envoy injection + mTLS detail |

## Mindset

**One-line takeaway:** An App Mesh virtual service is an abstraction
over a real service. A virtual node represents a deployable unit
(with DNS or Cloud Map service discovery). A virtual router directs
traffic to virtual nodes via weighted routes. Envoy sidecars (auto-
injected on EKS via a mutating webhook) enforce the routing, retry,
timeout, and mTLS policies. The control plane (App Mesh) pushes
configuration to Envoy via the xDS protocol.

Three misconceptions dominate App Mesh virtual service misdesign at
provisioning time:

- **"Virtual nodes and virtual services are the same."** They are
  NOT. A virtual node represents a concrete deployable unit (a
  Kubernetes Deployment, an ECS service, an EC2 fleet) with a service
  discovery mechanism (DNS hostname or Cloud Map service). A virtual
  service is an abstraction that clients call — it is backed by either
  a virtual node (direct routing, no traffic splitting) or a virtual
  router (weighted routing for canary/blue-green). The virtual service
  is the DNS name clients use; the virtual node is where traffic
  actually goes.

- **"Weighted routing works without a virtual router."** It does NOT.
  Traffic splitting (e.g., 90% to v1, 10% to v2 for canary) requires
  a virtual router with a weighted HTTP/TCP/gRPC route. If the
  virtual service points directly to a virtual node (no router), ALL
  traffic goes to that single node — no splitting is possible. This
  is the #1 cause of "my canary isn't working" — the virtual service
  has no router.

- **"Envoy sidecars are automatically injected on all platforms."**
  Only on EKS with the App Mesh Controller installed and the namespace
  labeled for injection. The controller installs a mutating admission
  webhook that injects the Envoy container into pods. On ECS, you
  must add the Envoy sidecar to the task definition manually. On EC2,
  you run Envoy as a process. Without the sidecar, mesh policies are
  NOT enforced — traffic flows directly, bypassing routing rules,
  retries, and mTLS.

## Configuration dependency graph (novel heuristic)

App Mesh virtual service configurations are NOT independent. The mesh
must exist before virtual nodes. Virtual nodes must exist before
virtual routers (routes reference them as targets). The virtual
service must reference either a node or a router. Envoy sidecars
must be injected for policies to take effect. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Service mesh | IAM appmesh:CreateMesh; unique mesh name | Egress filter DROP_ALL blocks all non-mesh egress by default | mesh container |
| Virtual node (DNS) | Mesh exists; DNS hostname resolvable | DNS hostname must point to the real service; no auto-registration | node with DNS discovery |
| Virtual node (Cloud Map) | Mesh exists; Cloud Map namespace + service exist | Cloud Map service must register instances; empty service = no endpoints | node with Cloud Map discovery (auto-registration) |
| Virtual router | Mesh exists | Router without routes = no traffic flows (virtual service backed by router gets 503) | routing layer |
| Weighted route | Router exists; two+ virtual nodes exist as targets | Weights must sum to 100; single-node route = all traffic to one node (no canary) | canary / blue-green traffic shifting |
| Virtual service | Mesh exists; backed by virtual node OR virtual router | Service pointing to a node (not router) = no traffic splitting possible | client-facing abstraction |
| Virtual gateway | Mesh exists; gateway listener configured | Gateway without gateway routes = no external traffic enters mesh | north-south ingress |
| Envoy sidecar (EKS) | App Mesh Controller installed; namespace labeled | Pods without sidecar = policies NOT enforced (traffic bypasses mesh) | policy enforcement |
| Envoy sidecar (ECS) | Envoy container in task definition; App Mesh proxy configuration | Missing Envoy = mesh policies silently bypassed | policy enforcement |
| mTLS (listener TLS) | ACM Private CA ACTIVE; virtual node/gateway listener TLS configured | mTLS in STRICT mode without valid client cert = all connections rejected | east-west/north-south encryption |
| mTLS (peer TLS) | ACM Private CA ACTIVE; SDS backend configured | Peer mTLS PERMISSIVE mode allows non-mTLS (migration); STRICT blocks | backpressure encryption |
| Circuit breaker | Virtual node backend defaults (connection pool, outlier detection) | Connection pool too low = healthy endpoints ejected; too high = no protection | fault isolation |

**The weighted-routing-requires-router row is the one a baseline
model misses.** Creating a virtual service that points directly to a
virtual node means NO traffic splitting is possible. The virtual
router with weighted routes is the ONLY mechanism for canary/blue-
green. The Envoy-sidecar-required row is the second commonly
misunderstood step.

**Cross-dependency gotchas:**
Cross-dependency gotchas moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when sequencing mesh, node, router, gateway, or mTLS provisioning.

## Expert heuristic: DNS vs Cloud Map service discovery

A baseline model says "pick any service discovery." The correct
heuristic recognizes that DNS and Cloud Map serve different use cases,
and the wrong choice causes stale backends or registration failures.

```text
Service discovery decision:
  ├── DNS service discovery
  │     → Virtual node specifies a DNS hostname (e.g., my-service.local)
  │     → Envoy resolves the hostname to get backend IPs
  │     → DNS TTL controls staleness (high TTL = stale endpoints)
  │     → Best for: services with stable IPs, ALB/NLB fronted services
  │     → No registration needed (DNS already resolves)
  │     → Limitation: DNS caching can delay backend removal
  │
  └── Cloud Map service discovery
        → Virtual node specifies a Cloud Map namespace + service name
        → Instances self-register with Cloud Map on startup
        → Envoy queries Cloud Map API for live backends
        → Best for: dynamic scaling (ECS, EKS, EC2 ASG)
        → Auto-registration: instances register/deregister on start/stop
        → Lower latency for endpoint changes (no DNS cache)
        → Requires: Cloud Map namespace + service created beforehand
```

**Key implication:** Cloud Map is the right choice for dynamic workloads
(ECS tasks, EKS pods that scale). DNS is simpler but stale for rapidly
changing backends. The virtual node's `serviceDiscovery` field
determines which mechanism is used — it CANNOT be both.

## Expert heuristic: weighted routing for canary deploy

A baseline model deploys v2 and hopes traffic shifts. The correct
heuristic recognizes that canary traffic shifting requires a virtual
router with weighted HTTP routes.

```text
Canary deploy flow with weighted routing:
  1. Virtual service "checkout.mesh.local" → virtual router
  2. Virtual router has HTTP route "checkout-route"
  3. Route initially: checkout-v1 (weight 100), checkout-v2 (weight 0)
  4. Deploy v2 (new virtual node "checkout-v2")
  5. Update route: checkout-v1 (weight 90), checkout-v2 (weight 10)
     → 10% of traffic goes to v2 (canary)
  6. Monitor metrics (error rate, latency) on v2
  7. If healthy: update to checkout-v1 (weight 50), checkout-v2 (weight 50)
  8. If healthy: update to checkout-v1 (weight 0), checkout-v2 (weight 100)
  9. v2 is now live; v1 can be scaled down

  WITHOUT a virtual router (virtual service → virtual node directly):
    → ALL traffic goes to the single node
    → NO canary possible (no traffic splitting mechanism)
    → Must swap the node's backend (instant cutover, no gradual shift)
```

**Key implication:** the virtual router is the ONLY mechanism for
weighted traffic splitting. A virtual service backed by a virtual
node (no router) cannot do canary. This is the #1 cause of "my canary
isn't working."

## Expert heuristic: Envoy sidecar auto-inject via webhook

Platform-by-platform injection detail moved verbatim to [references/envoy-and-mtls-guide.md](references/envoy-and-mtls-guide.md).
Load on demand when deciding EKS auto-inject vs ECS sidecar vs EC2 manual Envoy.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Service mesh name (unique in region) | Mesh names must be unique | `aws appmesh list-meshes` |
| Service discovery decision (DNS vs Cloud Map) | Determines virtual node config | Assess workload type |
| Cloud Map namespace exists (if Cloud Map) | Virtual node references it | `aws servicediscovery list-namespaces` |
| Cloud Map service exists (if Cloud Map) | Virtual node references it | `aws servicediscovery list-services` |
| DNS hostname resolvable (if DNS discovery) | Envoy resolves it for backends | `dig <hostname>` or `nslookup` |
| EKS cluster running (if EKS) | Envoy auto-inject needs cluster | `kubectl get nodes` |
| App Mesh Controller installed (if EKS) | Provides the mutating webhook | `kubectl get pods -n appmesh-system` |
| Namespace labeled for injection (if EKS auto-inject) | Webhook only fires on labeled namespaces | `kubectl get ns <ns> --show-labels` |
| ACM Private CA ACTIVE (if mTLS) | Issues Envoy certificates | `aws acm-pca list-certificate-authorities` |
| IAM appmesh:Create* permissions | Required for all create calls | Check IAM policy |
| Virtual node backend protocol (HTTP/TCP/gRPC) | Route type must match | Confirm protocol |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Service mesh creation

The service mesh is the top-level container for all virtual nodes,
routers, services, and gateways.

**Create the mesh:**

```bash
aws appmesh create-mesh \
  --mesh-name production-mesh \
  --spec '{"egressFilter":{"type":"ALLOW_ALL"}}' \
  --region us-east-1
```

**Egress filter options:**

| Filter | Behavior |
|---|---|
| ALLOW_ALL | Pods can reach any destination (mesh and non-mesh) |
| DROP_ALL | Pods can only reach mesh virtual services (all other egress blocked) |

**Critical:** DROP_ALL is more secure but breaks non-mesh dependencies
(database endpoints, external APIs). Start with ALLOW_ALL, then tighten
to DROP_ALL with explicit virtual services for allowed egress.

## Step 2 — Virtual nodes (DNS vs Cloud Map)

create-virtual-node CLI for both discovery modes moved verbatim to [references/service-discovery-and-routing.md](references/service-discovery-and-routing.md).
Load on demand when emitting virtual-node provisioning commands.

## Step 3 — Virtual routers and weighted routes

create-virtual-router and weighted create-route CLI moved verbatim to [references/service-discovery-and-routing.md](references/service-discovery-and-routing.md).
Load on demand when configuring canary traffic splitting.

## Step 4 — Route policies (timeout, retry)

Retry/timeout route-policy CLI and retry event types moved verbatim to [references/service-discovery-and-routing.md](references/service-discovery-and-routing.md).
Load on demand when adding resilience policies to a route.

## Step 5 — Circuit breaker and outlier detection

Circuit-breaker and outlier-detection payloads moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when configuring backendDefaults health checks or outlierDetection.

## Step 6 — Virtual services

A virtual service is the client-facing abstraction. It is backed by
either a virtual node (direct, no splitting) or a virtual router
(weighted routing).

**Virtual service backed by a virtual router (canary-capable):**

```bash
aws appmesh create-virtual-service \
  --mesh-name production-mesh \
  --virtual-service-name checkout.mesh.local \
  --spec '{
    "provider": {
      "virtualRouter": {
        "virtualRouterName": "checkout-router"
      }
    }
  }' \
  --region us-east-1
```

**Virtual service backed by a virtual node (no splitting):**

```bash
aws appmesh create-virtual-service \
  --mesh-name production-mesh \
  --virtual-service-name inventory.mesh.local \
  --spec '{
    "provider": {
      "virtualNode": {
        "virtualNodeName": "inventory-v1"
      }
    }
  }' \
  --region us-east-1
```

**Critical:** a virtual service backed by a virtual node CANNOT do
weighted routing. Only a virtual service backed by a virtual router
can split traffic. Choose the provider based on whether canary/blue-
green is needed.

## Step 7 — Virtual gateway (north-south ingress)

create-virtual-gateway and create-gateway-route CLI moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when provisioning north-south ingress.

## Step 8 — Envoy sidecar injection

EKS webhook install, ECS sidecar JSON, and the critical no-Envoy failure mode moved verbatim to [references/envoy-and-mtls-guide.md](references/envoy-and-mtls-guide.md).
Load on demand when injecting Envoy on any platform.

## Step 9 — mTLS via ACM Private CA

Listener TLS and backend peer TLS (SDS) payloads moved verbatim to [references/envoy-and-mtls-guide.md](references/envoy-and-mtls-guide.md).
Load on demand when enabling STRICT or PERMISSIVE mTLS.

## Step 10 — Observability (CloudWatch + X-Ray)

Access-log payload and Envoy metric names moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when wiring observability.

## Step 11 — Mesh scope (namespace vs cluster)

Namespace-scoping kubectl commands moved verbatim to [references/envoy-and-mtls-guide.md](references/envoy-and-mtls-guide.md).
Load on demand when scoping injection on EKS.

## Step 12 — xDS protocol

xDS flow walkthrough moved verbatim to [references/envoy-and-mtls-guide.md](references/envoy-and-mtls-guide.md).
Key implication kept here: route weight changes need no pod restarts — xDS pushes within seconds.

## Step 13 — Recent features

Recent AWS features (2023-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when evaluating newest App Mesh capabilities.

## NEVER do these things

1. **NEVER back a virtual service with a virtual node if you need
   canary routing.** Only a virtual router can do weighted traffic
   splitting. A virtual service backed by a virtual node sends ALL
   traffic to that single node.

2. **NEVER assume Envoy is auto-injected on all platforms.** Auto-
   inject works ONLY on EKS with the App Mesh Controller and labeled
   namespaces. ECS and EC2 require manual sidecar configuration.

3. **NEVER use mTLS STRICT mode during migration.** STRICT rejects
   all connections without valid certificates. Start with PERMISSIVE
   (allows mixing), verify all services have certs, then switch to
   STRICT.

4. **NEVER forget the Cloud Map namespace and service.** Cloud Map
   service discovery requires a pre-existing namespace and service.
   Without them, the virtual node has no backends and returns 503.

5. **NEVER use DROP_ALL egress filter without planning.** DROP_ALL
   blocks all non-mesh egress. If services depend on databases,
   external APIs, or S3, these connections will break unless explicit
   virtual services are created for allowed egress.

6. **NEVER assume route weight changes require pod restarts.** The
   xDS protocol pushes configuration changes in near-real-time via
   streaming. Weight changes take effect within seconds without
   restarts.

7. **NEVER confuse virtual node service discovery types.** DNS and
   Cloud Map are mutually exclusive — a virtual node uses ONE or the
   other. Mixing them is not supported.

8. **NEVER forget that Envoy resolves the DNS hostname at runtime.**
   DNS service discovery relies on the hostname being resolvable by
   Envoy. If DNS is misconfigured, Envoy has no backends.

9. **NEVER create a virtual gateway without gateway routes.** The
   virtual gateway is the listener; gateway routes direct traffic to
   virtual services. Without routes, no external traffic enters the
   mesh.

10. **NEVER set circuit breaker connection pool limits too low.**
    Low limits eject healthy endpoints under normal load. Start with
    generous limits and tune based on observed behavior.

## Output format

```text
APP_MESH: <mesh-name> — virtual service <vs-name> (<protocol>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Service mesh: <mesh-name> (egress: ALLOW_ALL | DROP_ALL)
  [✓|✗] Virtual node: <vn-name> (service discovery: DNS <hostname> | Cloud Map <namespace>/<service>)
  [✓|✗] Virtual router: <vr-name> (listener: <port>/<protocol>)
  [✓|✗] Weighted route: <route-name> — <vn-1> (<weight>%), <vn-2> (<weight>%)
  [✓|✗] Virtual service: <vs-name> → backed by <virtual-router | virtual-node>
  [✓|✗] Retry policy: maxRetries=<n>, perRetry=<ms>, events=<event-list>
  [✓|✗] Timeout: request=<value><unit>
  [✓|✗] Circuit breaker: healthCheck path=<path>, outlier detection maxServerErrors=<n>
  [✓|✗] Virtual gateway: <vgw-name> (listener: <port>/<protocol>)
  [✓|✗] Gateway route: <gr-name> → <virtual-service-name>
  [✓|✗] Envoy sidecar: auto-inject (EKS namespace=<ns>) | manual (ECS task | EC2)
  [✓|✗] mTLS: STRICT | PERMISSIVE | disabled (ACM Private CA <ca-arn>)
  [✓|✗] Observability: CloudWatch metrics enabled, X-Ray tracing enabled
  [✓|✗] Mesh ARN: arn:aws:appmesh:<region>:<acct>:mesh/<mesh-name>
VERIFICATION_COMMANDS:
  aws appmesh describe-mesh --mesh-name <mesh-name> --region <region>
  aws appmesh describe-virtual-node --mesh-name <mesh-name> --virtual-node-name <vn-name> --region <region>
  aws appmesh describe-route --mesh-name <mesh-name> --virtual-router-name <vr-name> --route-name <route-name> --region <region>
  aws appmesh describe-virtual-service --mesh-name <mesh-name> --virtual-service-name <vs-name> --region <region>
```

### Worked example — weighted canary with Cloud Map discovery and Envoy auto-inject

```text
APP_MESH: production-mesh — virtual service checkout.mesh.local (http)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Service mesh: production-mesh (egress: ALLOW_ALL)
  [✓] Virtual node: checkout-v1 (service discovery: Cloud Map mesh-services/checkout)
  [✓] Virtual node: checkout-v2 (service discovery: Cloud Map mesh-services/checkout-v2)
  [✓] Virtual router: checkout-router (listener: 8080/http)
  [✓] Weighted route: checkout-canary — checkout-v1 (90%), checkout-v2 (10%)
  [✓] Virtual service: checkout.mesh.local → backed by virtual-router checkout-router
  [✓] Retry policy: maxRetries=3, perRetry=2000ms, events=server-error,gateway-error
  [✓] Timeout: request=15s
  [✓] Circuit breaker: healthCheck path=/health, outlier detection maxServerErrors=5
  [✓] Envoy sidecar: auto-inject (EKS namespace=default, webhook=appmesh-controller)
  [✓] mTLS: PERMISSIVE (migration mode, ACM Private CA active)
  [✓] Observability: CloudWatch metrics enabled, X-Ray tracing enabled
  [✓] Mesh ARN: arn:aws:appmesh:us-east-1:123456789012:mesh/production-mesh
VERIFICATION_COMMANDS:
  aws appmesh describe-mesh --mesh-name production-mesh --region us-east-1
  aws appmesh describe-virtual-node --mesh-name production-mesh --virtual-node-name checkout-v1 --region us-east-1
  aws appmesh describe-route --mesh-name production-mesh --virtual-router-name checkout-router --route-name checkout-canary --region us-east-1
  aws appmesh describe-virtual-service --mesh-name production-mesh --virtual-service-name checkout.mesh.local --region us-east-1
```

## Error handling

Error-handling deep dives (503s, canary not splitting, Envoy not injected, mTLS rejected, DROP_ALL breakage, empty Cloud Map) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when a deployment or runtime failure must be diagnosed.

## References (load on demand)

- [references/service-discovery-and-routing.md](references/service-discovery-and-routing.md) — DNS vs Cloud Map and routing deep dive; now also holds Steps 2-4 (virtual nodes, weighted routes, route policies) moved from SKILL.md.
- [references/envoy-and-mtls-guide.md](references/envoy-and-mtls-guide.md) — Envoy injection and mTLS deep dive; now also holds the Envoy auto-inject heuristic and Steps 8, 9, 11, 12 moved from SKILL.md.
- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples moved from SKILL.md: circuit breaker (Step 5), virtual gateway (Step 7), observability (Step 10).
- [references/error-handling.md](references/error-handling.md) — error-handling deep dives moved from SKILL.md: 503 no healthy upstream, canary not splitting, Envoy not injected, mTLS rejections, DROP_ALL egress breakage, Cloud Map with no instances.
- [references/advanced-patterns.md](references/advanced-patterns.md) — cross-dependency gotchas and Recent AWS features 2023-2026 (Step 13) moved from SKILL.md.

## Domain

AWS CloudOps / AWS App Mesh Virtual Service Layer Provisioning &
Service Mesh Networking.

## AWS documentation

- **App Mesh User Guide** — https://docs.aws.amazon.com/app-mesh/latest/userguide/welcome.html
- **Virtual nodes** — https://docs.aws.amazon.com/app-mesh/latest/userguide/virtual_nodes.html
- **Virtual routers and routes** — https://docs.aws.amazon.com/app-mesh/latest/userguide/virtual_routers.html
- **Virtual services** — https://docs.aws.amazon.com/app-mesh/latest/userguide/virtual_services.html
- **Virtual gateways** — https://docs.aws.amazon.com/app-mesh/latest/userguide/virtual_gateways.html
- **Envoy proxy** — https://docs.aws.amazon.com/app-mesh/latest/userguide/envoy.html
- **mTLS** — https://docs.aws.amazon.com/app-mesh/latest/userguide/mtls.html
- **Cloud Map service discovery** — https://docs.aws.amazon.com/app-mesh/latest/userguide/cloudmap.html
- **App Mesh Controller for EKS** — https://docs.aws.amazon.com/app-mesh/latest/userguide/getting-started-kubernetes.html
- **CloudWatch metrics** — https://docs.aws.amazon.com/app-mesh/latest/userguide/metrics.html
