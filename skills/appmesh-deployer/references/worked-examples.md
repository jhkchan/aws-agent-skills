# App Mesh Worked Examples and CLI Boilerplate (load on demand)

Secondary worked example and common-pattern CLI boilerplate, moved verbatim from SKILL.md.
The primary worked example (weighted canary, READY_TO_DEPLOY) stays in SKILL.md.


## Worked example — mTLS missing CA (PREREQUISITES_MISSING)

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

## Common-pattern CLI boilerplate

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
