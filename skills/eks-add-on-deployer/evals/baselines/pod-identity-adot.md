# Baseline (no-skill) — pod-identity-adot

> This is the response a model produces **without** the skill
> definition. It mentions Pod Identity but misses the Pod Identity
> Agent add-on prerequisite, the trust principal difference
> (pods.eks.amazonaws.com), the association step, and the
> READY_TO_DEPLOY checklist format.

---

To use Pod Identity for ADOT:

1. Install the ADOT add-on.
2. Create a role and associate it.
3. That's it.

```bash
aws eks create-addon --cluster-name observability-cluster --addon-name adot
```
