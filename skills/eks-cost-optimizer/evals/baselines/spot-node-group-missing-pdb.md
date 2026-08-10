# Baseline (no-skill) response: spot-node-group-missing-pdb

This file captures what a generic assistant produces WITHOUT the
eks-cost-optimizer skill loaded.

---

Spot Instances can save you up to 90% on your EKS node costs. You can
create a Spot node group alongside your On-Demand group and use node
selectors to route pods to Spot nodes.

To set this up:

```bash
aws eks create-nodegroup \
  --cluster-name prod-cluster \
  --nodegroup-name spot-ng \
  --instance-types m5.2xlarge \
  --capacity-type SPOT \
  ...
```

Make sure to use multiple AZs for better availability. You should also
consider setting up pod disruption budgets for your deployments.
