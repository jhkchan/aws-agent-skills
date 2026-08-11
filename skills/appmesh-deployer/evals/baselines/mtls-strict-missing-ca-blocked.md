# Baseline (no-skill) response: mtls-strict-missing-ca-blocked

This file captures what a generic assistant produces WITHOUT the
appmesh-deployer skill loaded.

---

To enable STRICT mTLS on your virtual node listener:

```bash
aws appmesh update-virtual-node \
  --mesh-name prod-secure-mesh \
  --virtual-node-name checkout-service-v1 \
  --spec '{"listeners":[{"portMapping":{"port":8080,"protocol":"http"},"tls":{"mode":"STRICT","certificate":{"sds":{"secretName":"checkout-cert"}},"validation":{"trust":{"sds":{"secretName":"checkout-ca-bundle"}}}}}]}'
```

Make sure Envoy is configured with SDS for cert distribution.
