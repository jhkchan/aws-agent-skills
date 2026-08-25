# Envoy Injection and mTLS Guide — App Mesh Virtual Service Deployer

Deep reference on Envoy sidecar injection by platform (EKS auto-inject
via mutating webhook, ECS manual sidecar, EC2 manual process), the xDS
protocol (how App Mesh pushes configuration to Envoy), mTLS via ACM
Private CA (listener TLS, peer TLS, SDS, STRICT vs PERMISSIVE), and
observability (CloudWatch metrics, X-Ray tracing). Loaded on demand
by the skill — kept out of the main SKILL.md body so the provisioning
procedure stays scannable.

## Envoy sidecar injection

### EKS (auto-inject via mutating webhook)

The App Mesh Controller for EKS installs a MutatingWebhookConfiguration
that injects the Envoy sidecar container into pods created in labeled
namespaces.

**Install the controller (Helm):**

```bash
helm repo add eks https://aws.github.io/eks-charts
helm upgrade --install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --create-namespace \
  --set region=us-east-1 \
  --set serviceAccount.create=true \
  --set serviceAccount.name=appmesh-controller \
  --set tracer.enabled=true \
  --set tracer.provider=x-ray
```

**Verify the controller is running:**

```bash
kubectl get pods -n appmesh-system
# Expected: appmesh-controller-xxx Running
```

**Verify the webhook exists:**

```bash
kubectl get mutatingwebhookconfiguration
# Expected: appmesh-controller-... webhook
```

**Label the namespace for injection:**

```bash
kubectl label namespace default mesh=production-mesh appmesh=enabled
```

**Annotate the pod template:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: checkout-v1
  namespace: default
spec:
  selector:
    matchLabels:
      app: checkout-v1
  template:
    metadata:
      labels:
        app: checkout-v1
      annotations:
        appmesh.k8s.aws/virtualNode: checkout-v1
        # For virtual gateway pods:
        # appmesh.k8s.aws/virtualGateway: ingress-gateway
    spec:
      containers:
        - name: checkout
          image: checkout:1.0
          ports:
            - containerPort: 8080
```

**How injection works:**
1. Pod is created (e.g., via Deployment update).
2. The API server calls the mutating webhook (appmesh-controller).
3. The webhook checks the namespace labels (`mesh=`, `appmesh=enabled`).
4. If labeled, the webhook injects the Envoy sidecar container and
   init container (for iptables rules).
5. The init container sets up iptables to redirect traffic through Envoy.
6. Envoy starts and connects to App Mesh control plane via xDS.
7. App Mesh pushes the virtual node's configuration (routes, backends,
   policies) to Envoy via xDS streaming.

**Verifying injection:**

```bash
# Check that the Envoy sidecar is in the pod
kubectl get pods -n default -o jsonpath='{.items[0].spec.containers[*].name}'
# Expected: checkout envoy

# Check Envoy logs
kubectl logs <pod-name> -c envoy -n default
```

**Critical annotations:**
- `appmesh.k8s.aws/virtualNode: <node-name>` — maps the pod to a
  virtual node.
- `appmesh.k8s.aws/virtualGateway: <gateway-name>` — maps the pod to
  a virtual gateway (for ingress gateway pods).
- `appmesh.k8s.aws/ports: "8080"` — hints the controller about the
  application ports.

### ECS (manual sidecar)

On ECS, the Envoy sidecar must be added to the task definition manually.

```json
{
  "family": "checkout-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "proxyConfiguration": {
    "type": "APPMESH",
    "containerName": "envoy",
    "properties": [
      {"name": "IgnoredUID", "value": "1337"},
      {"name": "ProxyIngressPort", "value": "15000"},
      {"name": "ProxyEgressPort", "value": "15001"},
      {"name": "AppPorts", "value": "8080"},
      {"name": "EgressIgnoredIPs", "value": "169.254.170.2,169.254.169.254"}
    ]
  },
  "containerDefinitions": [
    {
      "name": "checkout",
      "image": "checkout:1.0",
      "portMappings": [{"containerPort": 8080}],
      "essential": true
    },
    {
      "name": "envoy",
      "image": "840364872350.dkr.ecr.us-east-1.amazonaws.com/aws-appmesh-envoy:v1.29.5.0-prod",
      "essential": true,
      "user": "1337",
      "environment": [
        {"name": "APPMESH_VIRTUAL_NODE_NAME", "value": "mesh/production-mesh/virtualNode/checkout-v1"},
        {"name": "ENVOY_LOG_LEVEL", "value": "info"}
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -s http://localhost:9901/server_info | grep state | grep -q LIVE"],
        "interval": 5,
        "timeout": 2,
        "retries": 3
      },
      "portMappings": [{"containerPort": 9901}]
    }
  ]
}
```

**Critical:** the `proxyConfiguration` with `type: APPMESH` is required
for ECS to set up the traffic redirection (iptables) so that traffic
flows through Envoy.

### EC2 (manual process)

On EC2, Envoy runs as a process alongside the application.

```bash
# Download Envoy
curl -L https://appmesh-<region>.s3.<region>.amazonaws.com/linux-x86_64/latest/appmesh-envoy -o /usr/local/bin/envoy
chmod +x /usr/local/bin/envoy

# Run Envoy pointing to the virtual node
ENVOY_LOG_LEVEL=info \
APPMESH_VIRTUAL_NODE_NAME=mesh/production-mesh/virtualNode/checkout-v1 \
/usr/local/bin/envoy
```

## xDS protocol

Envoy communicates with the App Mesh control plane via the xDS
(Discovery Service) protocol — a set of streaming gRPC connections
that push configuration in near-real-time.

### xDS endpoints

App Mesh exposes the following xDS endpoints:
- **CDS** (Cluster Discovery Service) — cluster/backend configurations
- **EDS** (Endpoint Discovery Service) — instance-level endpoints
- **LDS** (Listener Discovery Service) — listener configurations
- **RDS** (Route Discovery Service) — route configurations

### How configuration propagation works

```text
1. Operator updates a route weight (e.g., 90/10 → 50/50)
2. App Mesh control plane updates the route configuration
3. Control plane pushes the new RDS response to all Envoy instances
   via the xDS streaming connection
4. Each Envoy instance applies the updated routing table
5. New requests follow the updated weights (50/50)
6. Total propagation time: 1-5 seconds (no pod restart)

Key: xDS is streaming, not polling. Changes propagate fast.
```

**Key implication:** route weight changes, retry policy updates, and
new virtual node additions are all propagated via xDS within seconds.
There is NO need to restart pods or re-deploy for configuration changes.

### Verifying xDS connectivity

```bash
# Check Envoy admin interface (port 9901)
kubectl exec <pod> -c envoy -- curl http://localhost:9901/config_dump
# This shows the full configuration Envoy received via xDS

# Check cluster status
kubectl exec <pod> -c envoy -- curl http://localhost:9901/clusters
# This shows backend health and connection stats
```

## mTLS via ACM Private CA

### Listener TLS (inbound mTLS)

Listener TLS encrypts inbound traffic to a virtual node or virtual
gateway. The listener presents a server certificate.

```json
"listeners": [{
  "portMapping": {"port": 8080, "protocol": "http"},
  "tls": {
    "mode": "STRICT",
    "certificate": {
      "sds": {"secretName": "checkout-server-cert"}
    }
  }
}]
```

**mTLS modes:**
- `STRICT` — Envoy rejects all plaintext connections. All clients
  must present a valid certificate.
- `PERMISSIVE` — Envoy accepts both TLS and plaintext connections.
  Used for migration (mixing mTLS and non-mTLS services).

### Peer TLS (outbound mTLS)

Peer TLS encrypts outbound traffic from a virtual node to its backend
virtual services. The client (Envoy) presents a client certificate.

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

### ACM Private CA setup

```bash
# Create a private CA
CA_ARN=$(aws acm-pca create-certificate-authority \
  --certificate-authority-configuration '{
    "KeyAlgorithm": "RSA_2048",
    "SigningAlgorithm": "SHA256WITHRSA",
    "Subject": {"CN": "mesh-ca.example.com"}
  }' \
  --certificate-authority-type "ROOT" \
  --query 'CertificateAuthorityArn' --output text \
  --region us-east-1)

# Wait for CA status to become PENDING_CERTIFICATE
aws acm-pca describe-certificate-authority \
  --certificate-authority-arn "$CA_ARN" \
  --query 'CertificateAuthority.Status' \
  --region us-east-1

# Issue and install the root certificate
aws acm-pca get-certificate-authority-certificate \
  --certificate-authority-arn "$CA_ARN" \
  --region us-east-1
```

### SDS (Secret Discovery Service)

Envoy fetches TLS certificates via SDS. On EKS, SDS is typically backed
by Kubernetes Secrets or an external SDS provider (e.g., cert-manager).

```yaml
# Kubernetes Secret for the server certificate
apiVersion: v1
kind: Secret
metadata:
  name: checkout-server-cert
  namespace: default
data:
  tls.crt: <base64-encoded-cert>
  tls.key: <base64-encoded-key>
```

### Migration to mTLS

```text
Migration path:
  1. Deploy all services WITHOUT mTLS (plaintext mesh)
  2. Verify mesh routing, retries, circuit breaking work
  3. Deploy ACM Private CA and issue certificates
  4. Enable mTLS in PERMISSIVE mode (accepts both mTLS and plaintext)
  5. Verify all services can communicate in PERMISSIVE mode
  6. Gradually switch services to STRICT mode (one at a time)
  7. Verify each STRICT switch does not break dependent services
  8. All services are now STRICT — full mTLS mesh
```

**Critical:** switching to STRICT too early (before all dependencies
have certificates) causes connection rejections and service outages.
Always start with PERMISSIVE during migration.

## Observability

### CloudWatch metrics

App Mesh Envoy instances automatically emit metrics to CloudWatch.
Key metrics:

| Metric | Meaning |
|---|---|
| `envoy_cluster_upstream_rq_total` | Total request count |
| `envoy_cluster_upstream_rq_2xx` | Successful (2xx) responses |
| `envoy_cluster_upstream_rq_4xx` | Client error (4xx) responses |
| `envoy_cluster_upstream_rq_5xx` | Server error (5xx) responses |
| `envoy_cluster_upstream_rq_time` | Request latency (p50, p90, p99) |
| `envoy_cluster_health_check` | Health check success/failure |

**Enable metrics:** metrics are emitted by default when the Envoy
sidecar runs. No additional configuration needed.

### X-Ray tracing

X-Ray tracing provides distributed request tracing across mesh services.

**Enable X-Ray (EKS):**

```bash
# Install X-Ray daemon as a DaemonSet
kubectl apply -f https://github.com/aws/aws-xray-daemon/releases/download/v3.3.7/xray-k8s-daemonset.yaml
```

**Configure the App Mesh Controller for X-Ray:**

```bash
helm upgrade appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --set tracer.enabled=true \
  --set tracer.provider=x-ray
```

**Verify tracing in the X-Ray console:**
- Open X-Ray console in the AWS Management Console.
- View service map to see the mesh topology and traffic flow.
- View traces to see individual request paths through the mesh.

### Access logs

Envoy access logs can be directed to stdout for log aggregation:

```json
"listeners": [{
  "portMapping": {"port": 8080, "protocol": "http"},
  "accessLog": {
    "file": {"path": "/dev/stdout"}
  }
}]
```

## Common Envoy and mTLS pitfalls

1. **Namespace not labeled for injection.** The webhook only fires on
   namespaces labeled `mesh=<name> appmesh=enabled`. Without the label,
   no Envoy sidecar is injected, and mesh policies are NOT enforced.

2. **ECS task missing proxyConfiguration.** Without `proxyConfiguration`
   of type APPMESH, ECS does not set up traffic redirection through
   Envoy. Traffic flows directly, bypassing the mesh.

3. **mTLS STRICT without valid certificates.** STRICT mode rejects all
   connections without a valid client cert. Start with PERMISSIVE
   during migration.

4. **SDS not distributing certificates.** Envoy cannot fetch TLS
   certificates if SDS is not configured. Verify Kubernetes Secrets
   or the SDS provider has the certificates.

5. **Envoy cannot reach the control plane.** Envoy needs network
   connectivity to the App Mesh control plane endpoints. Verify
   security groups and network ACLs allow egress on the xDS port
   (443).

6. **xDS configuration not propagating.** If route changes are not
   taking effect, check Envoy's admin interface
   (`curl localhost:9901/config_dump`) to see what configuration it
   actually received.

---

## Expert heuristic: Envoy sidecar auto-inject via webhook (moved from SKILL.md)

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

---

## Step 8 — Envoy sidecar injection (moved from SKILL.md)

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

---

## Step 9 — mTLS via ACM Private CA (moved from SKILL.md)

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

---

## Step 11 — Mesh scope (namespace vs cluster) (moved from SKILL.md)

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

---

## Step 12 — xDS protocol (moved from SKILL.md)

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
