# End-to-end usage scenario: appmesh-deployer

A walkthrough showing the skill producing a deployment plan for a
production App Mesh service mesh with weighted canary routing,
virtual gateway ingress, mTLS for east-west traffic, circuit
breaking, and EKS sidecar injection via the App Mesh Controller.

## Input (user prompt)

> Provision an App Mesh service mesh `prod-checkout-mesh` in
> us-east-1. Use Cloud Map namespace `prod-internal` for service
> discovery. Create virtual nodes `checkout-service-v1` and
> `checkout-service-v2`, both with HTTP listener on port 8080 and
> health check on /health. Create virtual router `checkout-router`
> with a canary route `checkout-canary` at 90/10 (v1/v2), retry on
> gateway-error and 5xx with 3 retries and 2s perRetry, timeout
> request 5s idle 300s. Create virtual gateway `ingress-gateway`
> with HTTPS listener on 8443 and ACM cert abc123. Create gateway
> route `checkout-ingress` matching prefix /checkout. Enable STRICT
> mTLS via SDS with ACM Private CA. Configure connection pool
> (maxConnections 100, maxPendingRequests 50) and outlier detection
> (maxServerErrors 5, maxEjectionPercent 50) on the v1 listener.
> EKS namespace `prod` should be labeled for sidecar injection.

## Expected behavior

1. **Pre-flight:** The skill validates the spec — mesh name, Cloud
   Map namespace existence, ACM cert existence, ACM Private CA
   status, EKS namespace labeling, IAM permissions.
2. **Architecture output:** Mesh with DROP_ALL egress, two virtual
   nodes, one virtual router with canary route, virtual gateway
   with gateway route, STRICT mTLS via SDS, circuit breaking on v1
   listener, EKS sidecar injection.
3. **Verdict:** READY_TO_DEPLOY — all checklist dimensions pass.

## Expected output

```text
MESH_SPEC: prod-checkout-mesh
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Mesh: prod-checkout-mesh, egress_filter: DROP_ALL
  Virtual nodes: checkout-service-v1, checkout-service-v2 (Cloud Map prod-internal)
  Virtual router: checkout-router on port 8080
  Route: checkout-canary 90/10 (v1/v2), retry gateway-error + 5xx (3 retries, 2s perRetry), timeout request 5s idle 300s
  Virtual gateway: ingress-gateway on port 8443 HTTPS, ACM cert abc123
  Gateway route: checkout-ingress matching /checkout -> checkout virtual service
  mTLS: STRICT via SDS, ACM Private CA pca-xyz
  Circuit breaking: connection pool (100 conn, 50 pending) + outlier detection (5 errors, 50% eject)
  Sidecar: EKS controller injection on namespace prod
CHECKLIST:
  [x] Mesh egress filter DROP_ALL
  [x] Cloud Map namespace prod-internal exists (ID: ns-abc123)
  [x] Virtual nodes reference cloudMap serviceName checkout-v1, checkout-v2
  [x] Route weights sum to 100 (90 + 10)
  [x] Retry policy set (gateway-error, 5xx, 3 retries, 2s perRetry)
  [x] Timeout policy request 5s, idle 300s
  [x] Virtual gateway listener 8443 HTTPS, ACM cert abc123
  [x] Gateway route /checkout -> checkout virtual service
  [x] mTLS ACM Private CA pca-xyz ACTIVE
  [x] Circuit breaking connection pool + outlier detection on v1
  [x] EKS namespace prod labeled appmesh.k8s.aws/sidecarInjectorWebhook=enabled
FINDINGS:
  - [INFO] Canary 10% — monitor 5xx rate for 30 min before shifting to 100/0
  - [INFO] STRICT mTLS — verify SDS cert distribution before cutover
DEPLOY_COMMANDS:
  1. aws appmesh create-mesh --mesh-name prod-checkout-mesh --spec '{"egressFilter":{"type":"DROP_ALL"}}'
  2. aws appmesh create-virtual-node --mesh-name prod-checkout-mesh --virtual-node-name checkout-service-v1 --spec '<full spec>'
  3. aws appmesh create-virtual-node --mesh-name prod-checkout-mesh --virtual-node-name checkout-service-v2 --spec '<full spec>'
  4. aws appmesh create-virtual-router --mesh-name prod-checkout-mesh --virtual-router-name checkout-router --spec '<full spec>'
  5. aws appmesh create-route --mesh-name prod-checkout-mesh --virtual-router-name checkout-router --route-name checkout-canary --spec '<full spec>'
  6. aws appmesh create-virtual-gateway --mesh-name prod-checkout-mesh --virtual-gateway-name ingress-gateway --spec '<full spec>'
  7. aws appmesh create-gateway-route --mesh-name prod-checkout-mesh --virtual-gateway-name ingress-gateway --gateway-route-name checkout-ingress --spec '<full spec>'
```

## What the skill caught that a generic assistant misses

1. **Egress filter default.** A generic assistant omits the egress
   filter or sets `ALLOW_ALL`. The skill surfaces DROP_ALL as the
   production default and explains the implication (external deps
   need explicit virtual service backends).

2. **Virtual node != workload.** A generic assistant implies the
   virtual node deploys Envoy. The skill clarifies that Envoy
   deployment is separate (EKS controller injection, ECS task
   definition, EC2 binary).

3. **Retry budget vs timeout.** A generic assistant sets
   `per_request_timeout` 5s with 3 retries * 2s perRetry (= 6s) —
   request times out before retries complete. The skill ensures
   `per_request_timeout` >= retry budget + buffer.

4. **mTLS mode STRICT before SDS.** A generic assistant jumps to
   STRICT mode. The skill starts in PERMISSIVE, verifies SDS cert
   distribution, then switches to STRICT — avoiding a complete
   outage from misconfigured cert distribution.

5. **Circuit breaking paired with retries.** A generic assistant
   configures retries without outlier detection. The skill pairs
   them — retries multiply load during incidents; outlier detection
   auto-ejects unhealthy endpoints.

6. **ALB → gateway → mesh, not ALB → mesh members.** A generic
   assistant routes ALB directly to service pods. The skill routes
   ALB → gateway target group → gateway Envoy pods → mesh members,
   so mesh policies apply.

7. **Canary before blue/green.** A generic assistant may suggest
   100/0 → 0/100 cutover. The skill shifts 90/10 → 50/50 → 0/100
   progressively with observation windows.

8. **Snapshot before route update.** A generic assistant updates
   weights in place. The skill snapshots via `describe-route` first
   — no rollback path otherwise.

## Slash-command invocation

```
/aws:deploy-appmesh
```

Or via the orchestrator:

```
/aws:pipeline
You: "deploy an App Mesh with canary routing for checkout service"
```

The orchestrator emits
`[Phase: Deploy | Skills routed: appmesh-deployer]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "deploy App Mesh with weighted routing"
# [Phase: Deploy | Skills routed: appmesh-deployer]
```

## Live-account follow-up (optional, requires AWS CLI)

After the mesh is deployed:

```bash
# Verify the mesh
aws appmesh describe-mesh --mesh-name prod-checkout-mesh \
  --profile default \
  --query 'mesh.{Name:meshName,Egress:spec.egressFilter.type}' --output json

# Verify the canary route weights
aws appmesh describe-route --mesh-name prod-checkout-mesh \
  --virtual-router-name checkout-router --route-name checkout-canary \
  --profile default \
  --query 'route.spec.httpRoute.action.weightedTargets' --output table

# Verify the virtual gateway listener
aws appmesh describe-virtual-gateway --mesh-name prod-checkout-mesh \
  --virtual-gateway-name ingress-gateway \
  --profile default \
  --query 'virtualGateway.spec.listeners[0].{Port:portMapping.port,TLS:tls.mode}' --output json

# Verify EKS sidecar injection (2/2 READY means Envoy injected)
kubectl get pods -n prod -l app=checkout --show-labels
```
