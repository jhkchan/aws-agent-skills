# Baseline (no-skill) response: upgrade-addon-vpc-cni-bridge-version-ready

This file captures what a generic assistant produces WITHOUT the
eks-upgrade-operator skill loaded.

---

To upgrade the VPC-CNI add-on to v1.17.3-eksbuild.2:

```bash
aws eks update-addon \
  --cluster-name prod-cluster-01 \
  --addon-name vpc-cni \
  --addon-version v1.17.3-eksbuild.2 \
  --resolve-conflicts OVERWRITE
```

After the update completes, verify the daemonset is healthy.
