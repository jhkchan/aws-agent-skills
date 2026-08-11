# Baseline (no-skill) — core-addons-new-cluster

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses version compatibility
> verification, the IRSA trust policy detail (service account name),
> the configuration-values format, conflict resolution strategy, and
> the READY_TO_DEPLOY checklist format.

---

To set up core EKS add-ons:

```bash
aws eks create-addon --cluster-name production-cluster --addon-name vpc-cni
aws eks create-addon --cluster-name production-cluster --addon-name coredns
aws eks create-addon --cluster-name production-cluster --addon-name kube-proxy
```

For IRSA, create a role with the CNI policy and pass it:
```bash
aws eks create-addon --cluster-name production-cluster \
  --addon-name vpc-cni \
  --service-account-role-arn arn:aws:iam::123456789012:role/SomeRole
```
