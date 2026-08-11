# Baseline (no-skill) response: weighted-canary-ready

This file captures what a generic assistant produces WITHOUT the
appmesh-deployer skill loaded.

---

To create an App Mesh with weighted routing, use:

```bash
aws appmesh create-mesh --mesh-name prod-checkout-mesh

aws appmesh create-virtual-node --mesh-name prod-checkout-mesh \
  --virtual-node-name checkout-service-v1 \
  --spec '{"serviceDiscovery":{"cloudMap":{"namespaceName":"prod-internal","serviceName":"checkout-v1"}}}'

aws appmesh create-route --mesh-name prod-checkout-mesh \
  --virtual-router-name checkout-router --route-name checkout-canary \
  --spec '{"httpRoute":{"action":{"weightedTargets":[{"virtualNode":"checkout-service-v1","weight":90},{"virtualNode":"checkout-service-v2","weight":10}]}}}'
```

You'll need to set up the virtual router and the second virtual node too.
