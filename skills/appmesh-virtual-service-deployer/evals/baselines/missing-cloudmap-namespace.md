# Baseline (no-skill) — missing-cloudmap-namespace

> This is the response a model produces **without** the skill
> definition. It creates the virtual node referencing a Cloud Map
> namespace that does not exist, which will result in a silent
> failure (no backends registered, 503 errors when traffic is sent).
> Does not emit a PREREQUISITES_MISSING verdict. Generated for
> with-skill-vs-baseline comparison.

---

Create the virtual node:

```bash
aws appmesh create-virtual-node --mesh-name production-mesh \
  --virtual-node-name payments-v1 \
  --spec '{"serviceDiscovery":{"awsCloudMap":{"namespaceName":"payments-ns","serviceName":"payments"}},"listeners":[{"portMapping":{"port":8080,"protocol":"http"}}]}'
```

The node should start routing once payments register.
