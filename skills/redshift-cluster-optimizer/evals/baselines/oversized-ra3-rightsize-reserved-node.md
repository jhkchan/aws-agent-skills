# Baseline (no-skill) response: oversized-ra3-rightsize-reserved-node

This file captures what a generic assistant produces WITHOUT the
redshift-cluster-optimizer skill loaded.

---

Your Redshift cluster is running at 15% CPU on average, which suggests
it's overprovisioned. You could reduce the node count from 4 to 2 nodes
to save costs.

Here's how to resize:

```bash
aws redshift resize-cluster \
  --cluster-identifier analytics-prod-cluster \
  --cluster-type multi-node \
  --number-of-nodes 2 \
  --node-type ra3.4xlarge
```

You should also consider purchasing Reserved Instances to save up to 75%
on the compute cost. You can check available offerings with:

```bash
aws redshift describe-reserved-nodes-offerings
```

Make sure to monitor the cluster after resizing to ensure it handles
the workload.
