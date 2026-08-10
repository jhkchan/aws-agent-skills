# Baseline (no-skill) response: planned-failover-promote-replica-ready

This file captures what a generic assistant produces WITHOUT the
aurora-failover-operator skill loaded.

---

You can failover your Aurora cluster with:

```bash
aws rds failover-db-cluster \
  --db-cluster-identifier prod-orders-cluster \
  --target-db-instance-identifier prod-orders-node-2
```

This will promote node-2 to writer and demote node-1 to reader. The
failover should take about a minute. Your writer endpoint will
automatically point to the new writer.

Make sure to verify the cluster is available after the failover.
