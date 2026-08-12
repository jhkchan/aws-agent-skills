# Baseline (no-skill) response: network-policy-gap

This file captures what a generic assistant produces WITHOUT the
eks-security-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, severity rating, default-deny
warning about breaking traffic, canary rollout guidance, CONFIRM gate).

---

Your cluster has good pod-level security with PSA restricted-enforce and
IRSA on all namespaces. The main gap is that you have no network policies
at all, which means any pod can talk to any other pod in the cluster.

This is a significant risk for lateral movement. If an attacker
compromises one pod, they can reach every other pod without any network
restrictions.

You should install Calico or Cilium for network policy support. The
AWS VPC CNI doesn't implement Kubernetes NetworkPolicy on its own.

```
helm install calico projectcalico/tigera-operator -n tigera-operator --create-namespace
```

Then apply a default-deny policy in each namespace and add explicit allow
rules for the traffic flows your applications need.

Be careful with default-deny though — it will immediately block all
traffic that isn't explicitly allowed, which could break your workloads.
Test in a staging namespace first.

You might also want to switch App Mesh from permissive to strict mTLS
mode for pod-to-pod encryption.
