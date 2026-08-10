# Baseline (no-skill) response: pending-failedscheduling-taint

This file captures what a generic assistant produces WITHOUT the
eks-pod-troubleshooter skill loaded.

---

Your pod is Pending. This means Kubernetes can't schedule it onto a
node. The error says the nodes have taints the pod doesn't tolerate,
so the taints are blocking placement.

You can either add a toleration to your pod for the `dedicated=batch`
taint, or you can remove the taint from the nodes. To add a toleration:

```yaml
tolerations:
  - key: dedicated
    value: batch
    effect: NoSchedule
```

Also check that you have enough resources in your cluster.
