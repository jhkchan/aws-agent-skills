# Baseline (no-skill) response: virtual-gateway-ingress-ready

This file captures what a generic assistant produces WITHOUT the
appmesh-deployer skill loaded.

---

To create a virtual gateway:

```bash
aws appmesh create-virtual-gateway \
  --mesh-name prod-checkout-mesh \
  --virtual-gateway-name ingress-gateway \
  --spec '{"listeners":[{"portMapping":{"port":8443,"protocol":"http"}}]}'

aws appmesh create-gateway-route \
  --mesh-name prod-checkout-mesh \
  --virtual-gateway-name ingress-gateway \
  --gateway-route-name checkout-ingress \
  --spec '{"httpRoute":{"match":{"prefix":"/checkout"},"action":{"target":{"virtualService":{"virtualServiceName":"checkout.prod-checkout-mesh.svc.cluster.local"}}}}}'
```

Point your ALB at the gateway.
