---
description: Provision an AWS App Mesh virtual service layer with production-grade defaults (virtual nodes with DNS or Cloud Map service discovery, virtual routers with weighted routes for canary, Envoy sidecar auto-injection on EKS, virtual gateway ingress, mTLS via ACM Private CA, circuit breaking and outlier detection, CloudWatch and X-Ray observability). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create app mesh virtual service"
  - "deploy app mesh virtual service"
  - "app mesh virtual node"
  - "app mesh virtual router"
  - "weighted routing canary"
  - "app mesh envoy inject"
  - "app mesh mtls"
  - "virtual gateway ingress"
  - "app mesh cloud map discovery"
  - "app mesh dns discovery"
  - "app mesh circuit breaker"
  - "app mesh traffic shifting"
  - "deploy service mesh"
routes_to: appmesh-virtual-service-deployer
---

# /aws:deploy-appmesh-virtual-service

Activate the `appmesh-virtual-service-deployer` skill and provision an
AWS App Mesh virtual service layer with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Service mesh creation (egress filter DROP_ALL vs ALLOW_ALL)
2. Virtual nodes (DNS vs Cloud Map service discovery)
3. Virtual routers and weighted routes (canary traffic shifting)
4. Route policies (timeout, retry)
5. Circuit breaker and outlier detection
6. Virtual services (virtual node vs virtual router provider)
7. Virtual gateway (north-south ingress)
8. Envoy sidecar injection (EKS auto-inject, ECS manual, EC2 manual)
9. mTLS via ACM Private CA (STRICT vs PERMISSIVE)
10. Observability (CloudWatch metrics + X-Ray tracing)
11. Mesh scope (namespace vs cluster)
12. xDS protocol (control plane communication)

## When to use

- You need to create an App Mesh service mesh with virtual nodes and services.
- You are configuring weighted routing for canary or blue-green deployments.
- You need to set up a virtual gateway for external traffic ingress.
- You want Envoy sidecar auto-injection on EKS.
- You are enabling mTLS between mesh services.
- You need circuit breaker and outlier detection for fault isolation.
- You want CloudWatch metrics and X-Ray tracing for observability.

## When NOT to use

- **AWS Cloud Map without App Mesh** — use servicediscovery skills directly.
- **Istio service mesh** — different control plane (not AWS App Mesh).
- **AWS Gateway Load Balancer** — Layer 3/4 inspection, not a service mesh.
- **Network Load Balancer** — traffic distribution, not mesh routing.

## How to invoke

### Slash command

```
/aws:deploy-appmesh-virtual-service
```

Then provide: mesh name, virtual node names, service discovery type
(DNS or Cloud Map), virtual router name, route weights, virtual
service name, Envoy injection platform (EKS/ECS/EC2), mTLS
requirements, observability needs, region.

### Natural language

Any of these routes to the same skill:

- "create an app mesh virtual service with canary routing"
- "set up weighted routing between checkout v1 and v2"
- "configure cloud map service discovery for my mesh"
- "enable mTLS on my app mesh services"
- "inject envoy sidecars on my EKS namespace"

### CLI routing

```bash
node cli/bin/cli.js route "create an app mesh virtual service"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to provision App
Mesh virtual service layer resources. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-appmesh-virtual-service

     Create checkout.mesh.local in production-mesh. Canary
     90/10 between checkout-v1 and checkout-v2. DNS discovery.
     Retry 3, timeout 15s. EKS auto-inject on default namespace.

Skill:
  APP_MESH: production-mesh — virtual service checkout.mesh.local
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Virtual node: checkout-v1 (DNS checkout-v1.default.svc.cluster.local)
    [✓] Virtual node: checkout-v2 (DNS checkout-v2.default.svc.cluster.local)
    [✓] Weighted route: checkout-canary — v1 (90%), v2 (10%)
    [✓] Virtual service: checkout.mesh.local → virtual-router
    [✓] Envoy: auto-inject (EKS namespace=default)
  VERIFICATION_COMMANDS:
    aws appmesh describe-route --mesh-name production-mesh --virtual-router-name checkout-router --route-name checkout-canary --region us-east-1
    aws appmesh describe-virtual-service --mesh-name production-mesh --virtual-service-name checkout.mesh.local --region us-east-1
```

## References

- Skill definition: `skills/appmesh-virtual-service-deployer/SKILL.md`
- Service discovery and routing guide: `skills/appmesh-virtual-service-deployer/references/service-discovery-and-routing.md`
- Envoy and mTLS guide: `skills/appmesh-virtual-service-deployer/references/envoy-and-mtls-guide.md`
- Eval suite: `skills/appmesh-virtual-service-deployer/evals/evals.json`
