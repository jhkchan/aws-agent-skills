# Baseline (no-skill) — pod-identity-hybrid-workloads

> This is the response a model produces **without** the skill
> definition. It assumes pod identity works the same as managed node
> groups (wrong — hybrid nodes have no IMDS and need the pod identity
> agent explicitly installed), misses that EC2 instance profiles do not
> apply to on-prem nodes, and does not emit the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the pod identity association:

```bash
aws eks create-pod-identity-association --cluster-name prod-cluster
```

It should work the same as on managed node groups since IRSA uses
IMDS.
