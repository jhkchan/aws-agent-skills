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
- The virtual service DNS name (e.g., `service.mesh.local`) must
  match what clients call. If clients call `service.namespace.svc
  .cluster.local`, the virtual service must use that exact hostname.
- Cloud Map service discovery requires instances to self-register.
  If the Cloud Map service has no instances, the virtual node has no
  backends and traffic returns 503.
- The App Mesh Controller on EKS must be installed BEFORE labeling
  namespaces for injection. Labeling without the controller does
  nothing.
- mTLS STRICT mode on a virtual node rejects all connections that
  lack a valid client certificate. Start with PERMISSIVE mode during
  migration, then switch to STRICT.
- The egress filter on the mesh (DROP_ALL vs ALLOW_ALL) controls
  whether pods can talk to non-mesh services. DROP_ALL blocks all
  egress not explicitly allowed — plan for this or use ALLOW_ALL.

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

A baseline model assumes Envoy is always present. The correct
heuristic recognizes that auto-injection works ONLY on EKS with the
App Mesh Controller and namespace labeling. On ECS and EC2, manual
sidecar configuration is required.

```text
Envoy sidecar injection by platform:
  ├── EKS (auto-inject via mutating webhook)
  │     → Install App Mesh Controller (Helm chart)
  │     → Controller installs a MutatingWebhookConfiguration
  │     → Label namespace: kubectl label namespace app mesh=appmesh
  │     → Annotate pod: appmesh.k8s.aws/virtualNode: <node-name>
  │     → Webhook injects Envoy container into pods at creation
  │     → Envoy config pushed via xDS from App Mesh control plane
  │     → Pod restart NOT needed for route changes (xDS streaming)
  │
  ├── ECS (manual sidecar in task definition)
  │     → Add Envoy container to the task definition
  │     → Configure App Mesh proxy configuration (type=APPMESH)
  │     → Set ENVOY_LOG_LEVEL, APPMESH_VIRTUAL_NODE_NAME env vars
  │     → No webhook — must add to every task definition
  │
  └── EC2 (manual Envoy process)
        → Download and run Envoy binary
        → Configure with App Mesh bootstrap config
        → Point to the virtual node
        → No auto-inject — fully manual
```

**Key implication:** without the Envoy sidecar, NO mesh policies are
enforced. Traffic flows directly between services, bypassing routing
rules, retries, timeouts, circuit breakers, and mTLS. The sidecar is
the data plane — the control plane (App Mesh) configures it but does
not enforce policies directly.

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

A virtual node represents a deployable unit with service discovery.

**DNS service discovery:**

```bash
aws appmesh create-virtual-node \
  --mesh-name production-mesh \
  --virtual-node-name checkout-v1 \
  --spec '{
    "serviceDiscovery": {
      "dns": {
        "hostname": "checkout.default.svc.cluster.local"
      }
    },
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"}
    }],
    "backends": [
      {"virtualService": {"virtualServiceName": "inventory.mesh.local"}}
    ]
  }' \
  --region us-east-1
```

**Cloud Map service discovery:**

```bash
aws appmesh create-virtual-node \
  --mesh-name production-mesh \
  --virtual-node-name checkout-v1 \
  --spec '{
    "serviceDiscovery": {
      "awsCloudMap": {
        "namespaceName": "mesh-services",
        "serviceName": "checkout"
      }
    },
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"}
    }]
  }' \
  --region us-east-1
```

**Critical differences:**
- DNS: Envoy resolves the hostname; no instance registration needed.
  Best for stable IPs, ALB/NLB fronted services.
- Cloud Map: Instances self-register; Envoy queries Cloud Map for live
  backends. Best for dynamic scaling (ECS, EKS, EC2 ASG). Requires
  Cloud Map namespace + service created beforehand.

## Step 3 — Virtual routers and weighted routes

A virtual router holds route definitions that direct traffic to
virtual nodes with weights for canary/blue-green.

**Create a virtual router:**

```bash
aws appmesh create-virtual-router \
  --mesh-name production-mesh \
  --virtual-router-name checkout-router \
  --listeners '[{"portMapping":{"port":8080,"protocol":"http"}}]' \
  --region us-east-1
```

**Create a weighted HTTP route (canary):**

```bash
aws appmesh create-route \
  --mesh-name production-mesh \
  --virtual-router-name checkout-router \
  --route-name checkout-canary \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/"},
      "action": {
        "weightedTargets": [
          {"virtualNode": "checkout-v1", "weight": 90},
          {"virtualNode": "checkout-v2", "weight": 10}
        ]
      }
    }
  }' \
  --region us-east-1
```

**Critical:** the weights determine traffic splitting. 90/10 sends
10% to checkout-v2 (canary). Weights do NOT need to sum to 100 — they
are normalized. But conventionally they do sum to 100 for clarity.

## Step 4 — Route policies (timeout, retry)

Each route can have timeout and retry policies.

**Route with timeout and retry:**

```bash
aws appmesh create-route \
  --mesh-name production-mesh \
  --virtual-router-name checkout-router \
  --route-name checkout-resilient \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/"},
      "action": {
        "weightedTargets": [
          {"virtualNode": "checkout-v1", "weight": 100}
        ]
      },
      "retryPolicy": {
        "httpRetryEvents": ["server-error", "gateway-error"],
        "maxRetries": 3,
        "perRetryTimeout": {"unit": "ms", "value": 2000}
      },
      "timeout": {
        "request": {"unit": "s", "value": 15}
      }
    }
  }' \
  --region us-east-1
```

**Retry event types:**
- `server-error` — HTTP 5xx
- `gateway-error` — gateway-related errors (502, 503, 504)
- `client-error` — HTTP 4xx (retrying client errors is unusual)
- `stream-error` — retry on stream reset

## Step 5 — Circuit breaker and outlier detection

Circuit breaking is configured via virtual node backend defaults
(connection pool limits) and outlier detection (ejecting unhealthy
endpoints).

**Virtual node with circuit breaker:**

```bash
aws appmesh create-virtual-node \
  --mesh-name production-mesh \
  --virtual-node-name checkout-v1 \
  --spec '{
    "serviceDiscovery": {
      "awsCloudMap": {
        "namespaceName": "mesh-services",
        "serviceName": "checkout"
      }
    },
    "listeners": [{
      "portMapping": {"port": 8080, "protocol": "http"}
    }],
    "backendDefaults": {
      "clientPolicy": {
        "healthCheck": {
          "protocol": "http",
          "path": "/health",
          "healthyThreshold": 2,
          "unhealthyThreshold": 3,
          "timeoutMillis": 2000,
          "intervalMillis": 5000
        }
      }
    }
  }' \
  --region us-east-1
```

**Outlier detection** (ejecting unhealthy endpoints):

```json
"outlierDetection": {
  "maxServerErrors": 5,
  "interval": {"unit": "s", "value": 10},
  "baseEjectionDuration": {"unit": "s", "value": 30},
  "maxEjectionPercent": 50
}
```

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

A virtual gateway allows external traffic to enter the mesh.

**Create a virtual gateway:**

```bash
aws appmesh create-virtual-gateway \
  --mesh-name production-mesh \
  --virtual-gateway-name ingress-gateway \
  --spec '{
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
    }]
  }' \
  --region us-east-1
```

**Create a gateway route:**

```bash
aws appmesh create-gateway-route \
  --mesh-name production-mesh \
  --virtual-gateway-name ingress-gateway \
  --gateway-route-name checkout-ingress \
  --spec '{
    "httpRoute": {
      "action": {
        "target": {
          "virtualService": {
            "virtualServiceName": "checkout.mesh.local"
          }
        }
      },
      "match": {"prefix": "/checkout"}
    }
  }' \
  --region us-east-1
```

External traffic enters via the virtual gateway (fronted by ALB/NLB),
follows the gateway route to the virtual service, which routes through
the virtual router to the appropriate virtual node.

## Step 8 — Envoy sidecar injection

### EKS (auto-inject via mutating webhook)

**Install the App Mesh Controller (Helm):**

```bash
helm repo add eks https://aws.github.io/eks-charts
helm upgrade --install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --create-namespace \
  --set region=us-east-1 \
  --set serviceAccount.create=true \
  --set serviceAccount.name=appmesh-controller
```

**Label the namespace for injection:**

```bash
kubectl label namespace default mesh=production-mesh appmesh=enabled
```

**Annotate the pod's deployment:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: checkout-v1
spec:
  template:
    metadata:
      annotations:
        appmesh.k8s.aws/virtualNode: checkout-v1
    spec:
      containers:
        - name: checkout
          image: checkout:1.0
```

The mutating webhook injects the Envoy sidecar automatically when
pods are created in the labeled namespace.

### ECS (manual sidecar)

Add the Envoy container to the ECS task definition:

```json
{
  "name": "envoy",
  "image": "840364872350.dkr.ecr.us-east-1.amazonaws.com/aws-appmesh-envoy:v1.29.5.0-prod",
  "essential": true,
  "environment": [
    {"name": "APPMESH_VIRTUAL_NODE_NAME", "value": "mesh/production-mesh/virtualNode/checkout-v1"},
    {"name": "ENVOY_LOG_LEVEL", "value": "info"}
  ],
  "portMappings": [{"containerPort": 9901}]
}
```

**Critical:** without the Envoy sidecar, mesh policies are NOT
enforced. On ECS, forgetting the Envoy container is the #1 cause of
"mesh policies don't work."

## Step 9 — mTLS via ACM Private CA

mTLS encrypts east-west traffic between mesh services.

**Prerequisites:**
- ACM Private CA in ACTIVE state.
- Certificates issued for each virtual node.
- SDS (Secret Discovery Service) backend configured for Envoy to
  fetch certificates.

**Configure listener TLS (inbound mTLS):**

```json
"listeners": [{
  "portMapping": {"port": 8080, "protocol": "http"},
  "tls": {
    "mode": "STRICT",
    "certificate": {
      "sds": {
        "secretName": "checkout-cert"
      }
    }
  }
}]
```

**Configure backend peer TLS (outbound mTLS):**

```json
"backends": [{
  "virtualService": {
    "virtualServiceName": "inventory.mesh.local",
    "clientPolicy": {
      "tls": {
        "mode": "STRICT",
        "certificate": {
          "sds": {"secretName": "checkout-client-cert"}
        },
        "validation": {
          "trust": {
            "sds": {"secretName": "mesh-ca-bundle"}
          }
        }
      }
    }
  }
}]
```

**mTLS modes:**
- STRICT — rejects connections without valid certificates
- PERMISSIVE — accepts both mTLS and non-mTLS (for migration)

**Critical:** start with PERMISSIVE during migration (mixing mTLS and
non-mTLS services), then switch to STRICT once all services have
certificates. STRICT without valid certs = all connections rejected.

## Step 10 — Observability (CloudWatch + X-Ray)

App Mesh integrates with CloudWatch metrics and X-Ray tracing.

**Enable X-Ray tracing (virtual node listener):**

```json
"listeners": [{
  "portMapping": {"port": 8080, "protocol": "http"},
  "healthCheck": {...},
  "accessLog": {
    "file": {"path": "/dev/stdout"}
  }
}]
```

**CloudWatch metrics** are automatically emitted by Envoy:
- `envoy_cluster_upstream_rq_total` — request count
- `envoy_cluster_upstream_rq_2xx` — successful responses
- `envoy_cluster_upstream_rq_5xx` — server errors
- `envoy_cluster_upstream_rq_time` — latency distribution

**X-Ray tracing** requires the X-Ray daemon sidecar (EKS) or the
X-Ray integration in the Envoy configuration.

## Step 11 — Mesh scope (namespace vs cluster)

On EKS, the App Mesh Controller can scope mesh injection to specific
namespaces.

| Scope | Behavior | Use case |
|---|---|---|
| Namespace-level | Only labeled namespaces get injection | Mixed mesh/non-mesh workloads |
| Cluster-wide | All namespaces get injection | Full mesh adoption |

**Namespace scoping:**

```bash
# Enable injection for specific namespace
kubectl label namespace app-team mesh=production-mesh appmesh=enabled

# Disable for other namespaces (default: no injection)
kubectl label namespace monitoring appmesh=disabled --overwrite
```

## Step 12 — xDS protocol

Envoy communicates with the App Mesh control plane via the xDS
(Discovery Service) protocol. This is a streaming gRPC connection
that pushes configuration changes in near-real-time.

```text
xDS flow:
  1. Envoy starts and connects to App Mesh control plane via xDS
  2. App Mesh sends cluster, listener, route, endpoint configurations
  3. Envoy applies the configuration (no restart needed)
  4. Route weight change (e.g., canary 10% → 50%) is pushed via xDS
  5. Envoy updates its routing table within seconds
  6. New traffic follows the updated weights immediately

  Key: xDS is streaming (not polling). Config changes propagate fast.
```

**Key implication:** route weight changes do NOT require pod restarts.
The xDS streaming protocol pushes updates to all Envoy instances
within seconds. This is what makes canary traffic shifting near-
instantaneous.

## Step 13 — Recent features

**Recent AWS features (2023-2026):**

- **App Mesh Gateway Controller for EKS (2023-2024):** A CRD-based
  controller that allows declaring virtual gateways and gateway
  routes as Kubernetes resources, simplifying ingress configuration.

- **mTLS via SDS enhancement (2024-2025):** Improved Secret Discovery
  Service integration, allowing Envoy to fetch certificates from
  external SDS backends (not just Kubernetes secrets), enabling
  tighter integration with cert-manager and external CA systems.

- **Outlier detection improvements (2024-2025):** Enhanced outlier
  detection with configurable failure percentage thresholds and
  consecutive failure gating, giving finer control over endpoint
  ejection behavior.

- **App Mesh multi-cluster mesh (2025-2026):** Cross-cluster mesh
  connectivity via Cloud Map multi-cluster service discovery, allowing
  virtual nodes to span EKS clusters in different regions.

- **Envoy version upgrades (2025-2026):** App Mesh Envoy images
  updated to Envoy 1.30+ with improved HTTP/3 support and QUIC
  transport for mesh-internal traffic.

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

### Virtual service returns 503 (no healthy upstream)
- The virtual node has no backends. If using Cloud Map, verify
  instances are registered. If using DNS, verify the hostname
  resolves. Check health check configuration — failing health checks
  eject all endpoints.

### Canary traffic not splitting (all traffic to one node)
- The virtual service is backed by a virtual node, not a virtual
  router. Re-create the virtual service with a virtual router
  provider. Weighted routing requires the router.

### Envoy not injected (EKS)
- The namespace is not labeled for injection. Run
  `kubectl label namespace <ns> mesh=<mesh-name> appmesh=enabled`.
  Verify the App Mesh Controller is running in appmesh-system
  namespace.

### mTLS connections rejected (STRICT mode)
- Not all services have valid certificates. Switch to PERMISSIVE
  mode, issue certificates via ACM Private CA for all virtual nodes,
  verify SDS is distributing certs, then switch back to STRICT.

### DROP_ALL egress filter breaks database connectivity
- The mesh blocks all non-mesh egress. Create a virtual service for
  the database endpoint (with a virtual node using DNS discovery
  pointing to the database hostname), or switch to ALLOW_ALL egress.

### Cloud Map service has no instances
- Instances are not self-registering. For ECS, verify the task has
  Cloud Map service registration enabled. For EC2, verify the
  instance runs the Cloud Map registration agent. For EKS, verify
  the App Mesh Controller registers pods to Cloud Map.

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
