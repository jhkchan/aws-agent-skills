# Baseline (no-skill) response: upgrade-nodegroup-pdb-blocks-drain-blocked

This file captures what a generic assistant produces WITHOUT the
eks-upgrade-operator skill loaded.

---

To upgrade your node group to 1.29:

```bash
aws eks update-nodegroup-version \
  --cluster-name prod-cluster-01 \
  --nodegroup-name prod-ng-1 \
  --kubernetes-version 1.29
```

If the upgrade is stuck, check whether any PodDisruptionBudgets are
blocking pod eviction.
