# Baseline (no-skill) — envoy-auto-inject-webhook

> This is the response a model produces **without** the skill
> definition. It installs the controller but does not label the
> namespace for injection (without the label, the webhook does NOT
> fire and Envoy is NOT injected), and omits the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Install the controller:

```bash
helm repo add eks https://aws.github.io/eks-charts
helm install appmesh-controller eks/appmesh-controller -n appmesh-system --create-namespace
```

Then create the virtual node:

```bash
aws appmesh create-virtual-node --mesh-name production-mesh \
  --virtual-node-name api-v1 \
  --spec '{"serviceDiscovery":{"dns":{"hostname":"api.default.svc.cluster.local"}},"listeners":[{"portMapping":{"port":8080,"protocol":"http"}}]}'
```

The sidecar should be injected automatically.
