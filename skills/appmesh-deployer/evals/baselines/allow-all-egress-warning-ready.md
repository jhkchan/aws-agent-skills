# Baseline (no-skill) response: allow-all-egress-warning-ready

This file captures what a generic assistant produces WITHOUT the
appmesh-deployer skill loaded.

---

To create the dev mesh with ALLOW_ALL egress:

```bash
aws appmesh create-mesh \
  --mesh-name dev-test-mesh \
  --spec '{"egressFilter":{"type":"ALLOW_ALL"}}'

aws appmesh create-virtual-node --mesh-name dev-test-mesh \
  --virtual-node-name api-service-v1 \
  --spec '{"serviceDiscovery":{"cloudMap":{"namespaceName":"dev-internal","serviceName":"api-v1"}},"listeners":[{"portMapping":{"port":8080,"protocol":"http"}}]}'

aws appmesh create-route --mesh-name dev-test-mesh \
  --virtual-router-name api-router --route-name api-default \
  --spec '{"httpRoute":{"action":{"weightedTargets":[{"virtualNode":"api-service-v1","weight":100}]}}}'
```

ALLOW_ALL is fine for dev.
