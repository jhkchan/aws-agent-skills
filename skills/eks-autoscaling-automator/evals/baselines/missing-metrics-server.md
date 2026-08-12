# Baseline (no-skill) response: missing-metrics-server

This file captures what a generic assistant produces WITHOUT the
eks-autoscaling-automator skill loaded.

---

You can set up autoscaling for your staging cluster. First, install
the metrics-server so you can use HPA:

```
helm install metrics-server metrics-server/metrics-server --namespace kube-system
```

Then install Cluster Autoscaler or Karpenter to handle node scaling.
For a small staging cluster, Cluster Autoscaler might be simpler.

Set up HPA for your workloads to scale based on CPU usage. Make sure
your node group has a min and max size so the autoscaler can add and
remove nodes as needed.

You might also want to consider using spot instances to save costs,
even in staging.
