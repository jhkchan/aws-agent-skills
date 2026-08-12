# Baseline (no-skill) — weighted-canary-dns-discovery

> This is the response a model produces **without** the skill
> definition. It creates virtual nodes and a route but misses that
> the virtual service MUST be backed by a virtual router (not a
> virtual node) for weighted splitting to work, omits the retry
> and timeout policies, and does not emit the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the virtual nodes and route:

```bash
aws appmesh create-virtual-node --mesh-name production-mesh \
  --virtual-node-name checkout-v1 --spec '{"serviceDiscovery":{"dns":{"hostname":"checkout-v1.default.svc.cluster.local"}}}'

aws appmesh create-virtual-node --mesh-name production-mesh \
  --virtual-node-name checkout-v2 --spec '{"serviceDiscovery":{"dns":{"hostname":"checkout-v2.default.svc.cluster.local"}}}'

aws appmesh create-route --mesh-name production-mesh \
  --virtual-router-name checkout-router --route-name checkout \
  --spec '{"httpRoute":{"action":{"weightedTargets":[{"virtualNode":"checkout-v1","weight":90},{"virtualNode":"checkout-v2","weight":10}]}}}'
```

That should give you canary traffic.
