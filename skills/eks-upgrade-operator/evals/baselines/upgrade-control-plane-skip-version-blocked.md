# Baseline (no-skill) response: upgrade-control-plane-skip-version-blocked

This file captures what a generic assistant produces WITHOUT the
eks-upgrade-operator skill loaded.

---

To upgrade your EKS cluster from 1.27 to 1.29:

```bash
aws eks update-cluster-version \
  --name prod-cluster-01 \
  --kubernetes-version 1.29
```

You may need to first upgrade to 1.28 before going to 1.29.
