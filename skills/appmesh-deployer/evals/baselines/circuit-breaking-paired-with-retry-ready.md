# Baseline (no-skill) response: circuit-breaking-paired-with-retry-ready

This file captures what a generic assistant produces WITHOUT the
appmesh-deployer skill loaded.

---

To add circuit breaking to your virtual node:

```bash
aws appmesh update-virtual-node \
  --mesh-name prod-checkout-mesh \
  --virtual-node-name checkout-service-v1 \
  --spec '{"listeners":[{"portMapping":{"port":8080,"protocol":"http"},"connectionPool":{"http":{"maxConnections":100,"maxPendingRequests":50}},"outlierDetection":{"maxServerErrors":5,"intervalMillis":10000,"baseEjectionDurationMillis":30000,"maxEjectionPercent":50}}]}'
```

This pairs well with your existing retry policy.
