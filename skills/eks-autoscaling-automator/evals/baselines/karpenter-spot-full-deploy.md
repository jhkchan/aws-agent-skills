# Baseline (no-skill) response: karpenter-spot-full-deploy

This file captures what a generic assistant produces WITHOUT the
eks-autoscaling-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, Karpenter manifests,
spot diversification, disruption budgets, HPA behavior tuning,
overprovisioning, expert EKS knowledge).

---

For your EKS cluster, I'd recommend installing Karpenter for node
autoscaling and setting up HPA for your workloads. Karpenter is
better than Cluster Autoscaler because it's faster and handles spot
instances well.

To install Karpenter:

```
helm install karpenter oci://public.ecr.aws/karpenter/karpenter --namespace kube-system
```

Then create a NodePool that uses spot instances. You can set the
capacity type to spot and let Karpenter pick the instance types.

For HPA on your api-server:

```
kubectl autoscale deployment api-server --cpu-percent=70 --min=3 --max=50
```

For the SQS consumer, you might want to use KEDA to scale based on
queue depth. Install KEDA via Helm and create a ScaledObject.

For overprovisioning, you can create some pause pods with low priority
to keep headroom. Make sure the priority is lower than your real
workloads.

Don't forget to set up pod disruption budgets to protect your pods
during node drains.
