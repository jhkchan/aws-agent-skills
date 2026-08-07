# Baseline (no-skill) response: upgrade-control-plane-1-28-to-1-29-ready

This file captures what a generic assistant produces WITHOUT the
eks-upgrade-operator skill loaded.

---

To upgrade your EKS cluster from 1.28 to 1.29, use the following command:

```bash
aws eks update-cluster-version \
  --name prod-cluster-01 \
  --kubernetes-version 1.29
```

You can check the status with:

```bash
aws eks describe-update --name prod-cluster-01
```

After the control plane is upgraded, you'll want to upgrade your node
groups and add-ons to match.
