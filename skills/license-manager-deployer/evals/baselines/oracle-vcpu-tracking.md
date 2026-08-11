# Baseline (no-skill) — oracle-vcpu-tracking

> This is the response a model produces **without** the skill
> definition. It creates the license configuration but misses the
> Oracle vendor-specific license rules (Tenancy, HonorVcpuOptimization),
> the cross-Org enablement prerequisites (Organizations all-features,
> License Manager trusted service, delegated administrator), the SSM
> inventory requirement for discovery, and the EventBridge alerting
> setup. Does not emit a READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Sure, here's the license config:

```bash
aws license-manager create-license-configuration \
  --name "oracle-db" \
  --license-counting-type vCPU \
  --license-count 200
```

You can share it across accounts if you want.
