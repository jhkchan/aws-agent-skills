# End-to-End Example: App Mesh Virtual Service Deployment

A walkthrough showing how to use the `appmesh-virtual-service-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an App Mesh virtual service with a weighted canary
deployment (90/10 split between v1 and v2), DNS service discovery on
both virtual nodes, retry and timeout policies, and Envoy sidecar auto-
injection on EKS. The mesh needs:

- Mesh name: production-mesh (egress: ALLOW_ALL)
- Virtual nodes: checkout-v1 and checkout-v2 (DNS discovery)
- Virtual router: checkout-router (weighted HTTP route)
- Virtual service: checkout.mesh.local → backed by virtual router
- Canary: 90% checkout-v1, 10% checkout-v2
- Retry: maxRetries=3, perRetry=2000ms
- Timeout: request=15s
- Envoy: auto-inject on EKS (namespace default)
- Region: us-east-1
- Account: 123456789012

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-appmesh-virtual-service
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an App Mesh virtual service checkout.mesh.local
      with a 90/10 canary between checkout-v1 and checkout-v2.
      DNS discovery, retry 3, timeout 15s. EKS auto-inject."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an app mesh virtual service"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
APP_MESH: production-mesh — virtual service checkout.mesh.local (http)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Service mesh: production-mesh (egress: ALLOW_ALL)
  [✓] Virtual node: checkout-v1 (service discovery: DNS checkout-v1.default.svc.cluster.local)
  [✓] Virtual node: checkout-v2 (service discovery: DNS checkout-v2.default.svc.cluster.local)
  [✓] Virtual router: checkout-router (listener: 8080/http)
  [✓] Weighted route: checkout-canary — checkout-v1 (90%), checkout-v2 (10%)
  [✓] Virtual service: checkout.mesh.local → backed by virtual-router checkout-router
  [✓] Retry policy: maxRetries=3, perRetry=2000ms, events=server-error,gateway-error
  [✓] Timeout: request=15s
  [✓] Envoy sidecar: auto-inject (EKS namespace=default, webhook=appmesh-controller)
  [✓] Observability: CloudWatch metrics enabled, X-Ray tracing enabled
  [✓] Mesh ARN: arn:aws:appmesh:us-east-1:123456789012:mesh/production-mesh
VERIFICATION_COMMANDS:
  aws appmesh describe-mesh --mesh-name production-mesh --region us-east-1
  aws appmesh describe-route --mesh-name production-mesh --virtual-router-name checkout-router --route-name checkout-canary --region us-east-1
  aws appmesh describe-virtual-service --mesh-name production-mesh --virtual-service-name checkout.mesh.local --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the mesh
aws appmesh create-mesh \
  --mesh-name production-mesh \
  --spec '{"egressFilter":{"type":"ALLOW_ALL"}}' \
  --region us-east-1

# Step 2: Create virtual node checkout-v1 (DNS discovery)
aws appmesh create-virtual-node \
  --mesh-name production-mesh \
  --virtual-node-name checkout-v1 \
  --spec '{
    "serviceDiscovery": {"dns": {"hostname": "checkout-v1.default.svc.cluster.local"}},
    "listeners": [{"portMapping": {"port": 8080, "protocol": "http"}}]
  }' \
  --region us-east-1

# Step 3: Create virtual node checkout-v2 (DNS discovery)
aws appmesh create-virtual-node \
  --mesh-name production-mesh \
  --virtual-node-name checkout-v2 \
  --spec '{
    "serviceDiscovery": {"dns": {"hostname": "checkout-v2.default.svc.cluster.local"}},
    "listeners": [{"portMapping": {"port": 8080, "protocol": "http"}}]
  }' \
  --region us-east-1

# Step 4: Create the virtual router
aws appmesh create-virtual-router \
  --mesh-name production-mesh \
  --virtual-router-name checkout-router \
  --listeners '[{"portMapping":{"port":8080,"protocol":"http"}}]' \
  --region us-east-1

# Step 5: Create the weighted HTTP route (canary 90/10)
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

# Step 6: Create the virtual service (backed by virtual router)
aws appmesh create-virtual-service \
  --mesh-name production-mesh \
  --virtual-service-name checkout.mesh.local \
  --spec '{
    "provider": {
      "virtualRouter": {"virtualRouterName": "checkout-router"}
    }
  }' \
  --region us-east-1
```

---

## Step 4 — EKS Envoy auto-injection setup

```bash
# Install the App Mesh Controller (Helm)
helm repo add eks https://aws.github.io/eks-charts
helm upgrade --install appmesh-controller eks/appmesh-controller \
  --namespace appmesh-system \
  --create-namespace \
  --set region=us-east-1 \
  --set tracer.enabled=true \
  --set tracer.provider=x-ray

# Label the namespace for injection
kubectl label namespace default mesh=production-mesh appmesh=enabled

# Deploy checkout-v1 with the virtual node annotation
# (the webhook injects Envoy automatically)
kubectl apply -f - <<EOF
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
    spec:
      containers:
        - name: checkout
          image: checkout:1.0
          ports:
            - containerPort: 8080
EOF
```

---

## Step 5 — Canary progression

```bash
# Shift canary from 10% to 50%
aws appmesh update-route \
  --mesh-name production-mesh \
  --virtual-router-name checkout-router \
  --route-name checkout-canary \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/"},
      "action": {
        "weightedTargets": [
          {"virtualNode": "checkout-v1", "weight": 50},
          {"virtualNode": "checkout-v2", "weight": 50}
        ]
      }
    }
  }' \
  --region us-east-1

# Complete the canary (100% to v2)
aws appmesh update-route \
  --mesh-name production-mesh \
  --virtual-router-name checkout-router \
  --route-name checkout-canary \
  --spec '{
    "httpRoute": {
      "match": {"prefix": "/"},
      "action": {
        "weightedTargets": [
          {"virtualNode": "checkout-v1", "weight": 0},
          {"virtualNode": "checkout-v2", "weight": 100}
        ]
      }
    }
  }' \
  --region us-east-1
```

---

## Step 6 — Post-deployment verification

```bash
# Verify the mesh
aws appmesh describe-mesh \
  --mesh-name production-mesh \
  --region us-east-1

# Verify the route weights
aws appmesh describe-route \
  --mesh-name production-mesh \
  --virtual-router-name checkout-router \
  --route-name checkout-canary \
  --query 'route.spec.httpRoute.action.weightedTargets' \
  --region us-east-1

# Verify the virtual service
aws appmesh describe-virtual-service \
  --mesh-name production-mesh \
  --virtual-service-name checkout.mesh.local \
  --region us-east-1

# Verify Envoy injection (EKS)
kubectl get pods -n default -o jsonpath='{.items[0].spec.containers[*].name}'
# Expected: checkout envoy
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Virtual service provider | Virtual node (no splitting) | Virtual router (canary-capable) | Only router-backed services can split traffic |
| Envoy injection | Assumes auto-inject everywhere | Namespace label + controller required | Without label, webhook does not fire; policies not enforced |
| Retry policy | Not configured | maxRetries=3 with perRetry timeout | Retries improve resilience under transient failures |
| Timeout | No timeout | request=15s | Without timeout, hung requests consume connections indefinitely |
| xDS propagation | Assumes pod restart needed | xDS streaming pushes changes in seconds | Route updates take effect without restarts |
| DNS hostname | Wrong hostname | Matches client-call name | Envoy resolves at runtime; wrong hostname = no backends |

---

## Related artifacts

- **Skill definition:** `skills/appmesh-virtual-service-deployer/SKILL.md`
- **Service discovery and routing guide:** `skills/appmesh-virtual-service-deployer/references/service-discovery-and-routing.md`
- **Envoy and mTLS guide:** `skills/appmesh-virtual-service-deployer/references/envoy-and-mtls-guide.md`
- **Slash command:** `commands/aws/deploy-appmesh-virtual-service.md`
- **Eval suite:** `skills/appmesh-virtual-service-deployer/evals/evals.json`
- **Legacy test cases:** `skills/appmesh-virtual-service-deployer/eval/test-cases.yaml`
