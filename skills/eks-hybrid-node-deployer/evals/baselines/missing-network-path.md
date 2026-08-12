# Baseline (no-skill) — missing-network-path

> This is the response a model produces **without** the skill
> definition. It proceeds with registration without flagging that the
> on-prem servers cannot reach the EKS API endpoint (no Direct Connect
> or VPN; private endpoint only). Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Sure, register the nodes:

```bash
aws eks create-access-entry --cluster-name prod-cluster
```

The nodes should be able to reach the cluster over the internet.
