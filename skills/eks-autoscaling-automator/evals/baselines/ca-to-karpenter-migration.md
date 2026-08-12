# Baseline (no-skill) response: ca-to-karpenter-migration

This file captures what a generic assistant produces WITHOUT the
eks-autoscaling-automator skill loaded.

---

To migrate from Cluster Autoscaler to Karpenter, first uninstall
Cluster Autoscaler:

```
helm uninstall cluster-autoscaler -n kube-system
```

Then install Karpenter:

```
helm install karpenter oci://public.ecr.aws/karpenter/karpenter --namespace kube-system --set clusterName=prod-cluster
```

Create a NodePool and EC2NodeClass for Karpenter to know what kind of
nodes to provision. You can use spot instances and set up
consolidation to optimize costs.

Make sure your existing HPA configurations continue to work. Karpenter
should handle the node provisioning side while HPA handles pod scaling.

For spot interruption handling, Karpenter has built-in support so you
don't need the Node Termination Handler anymore.
