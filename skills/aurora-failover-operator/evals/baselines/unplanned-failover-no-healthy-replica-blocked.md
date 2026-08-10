# Baseline (no-skill) response: unplanned-failover-no-healthy-replica-blocked

This file captures what a generic assistant produces WITHOUT the
aurora-failover-operator skill loaded.

---

Since your primary is unreachable and the only replica is still creating,
you should wait for prod-checkout-node-2 to finish creating, then run the
failover:

```bash
aws rds failover-db-cluster \
  --db-cluster-identifier prod-checkout-cluster
```

If node-2 doesn't become available soon, you may need to restore from a
snapshot.
