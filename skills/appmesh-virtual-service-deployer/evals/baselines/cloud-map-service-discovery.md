# Baseline (no-skill) — cloud-map-service-discovery

> This is the response a model produces **without** the skill
> definition. It creates the virtual node but does not verify that
> the Cloud Map namespace and service exist beforehand (the node
> will have no backends without registration), and omits the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the virtual node:

```bash
aws appmesh create-virtual-node --mesh-name production-mesh \
  --virtual-node-name inventory-v1 \
  --spec '{"serviceDiscovery":{"awsCloudMap":{"namespaceName":"mesh-services","serviceName":"inventory"}},"listeners":[{"portMapping":{"port":8080,"protocol":"http"}}]}'
```

Then create the virtual service pointing to it.
