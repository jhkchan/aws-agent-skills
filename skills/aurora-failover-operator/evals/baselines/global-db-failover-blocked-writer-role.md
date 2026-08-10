# Baseline (no-skill) response: global-db-failover-blocked-writer-role

This file captures what a generic assistant produces WITHOUT the
aurora-failover-operator skill loaded.

---

You can failover within us-east-1 to promote prod-global-node-2:

```bash
aws rds failover-db-cluster \
  --db-cluster-identifier prod-global-primary \
  --target-db-instance-identifier prod-global-node-2
```

This will promote node-2 to writer. Since you have a Global Database,
make sure the secondary region (eu-west-1) stays in sync after the
failover.
