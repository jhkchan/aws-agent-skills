# Baseline (no-skill) response: failback-to-original-primary-ready

This file captures what a generic assistant produces WITHOUT the
aurora-failover-operator skill loaded.

---

You can failback to node-1 by running another failover:

```bash
aws rds failover-db-cluster \
  --db-cluster-identifier prod-orders-cluster \
  --target-db-instance-identifier prod-orders-node-1
```

This will promote node-1 back to writer. Node-2 will become a reader
again. The failover should take about a minute, during which writes will
be briefly interrupted.
