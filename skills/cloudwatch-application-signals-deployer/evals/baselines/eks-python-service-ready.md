# Baseline (no-skill) — eks-python-service-ready

> This is the response a model produces **without** the skill definition.
> It produces generic OTel Operator install steps but misses the
> Kubernetes attributes processor configuration, the dual-SLO
> (availability + latency) structure, the burn-rate alarm thresholds,
> and the IRSA-attached IAM policy verification.

---

For EKS Python, install the OTel Operator via Helm:

```bash
helm install opentelemetry-operator open-telemetry/opentelemetry-operator \
  --namespace opentelemetry-operator-system --create-namespace
```

Then annotate your deployment:

```bash
kubectl annotate deploy search-api \
  instrumentation.opentelemetry.io/inject-python="true"
```

Make sure your service account has IAM roles via IRSA. Then create
your SLOs — one for availability and one for p95 latency.
