# Baseline (no-skill) response: remove-replica-blocked-active-traffic

This file captures what a generic assistant produces WITHOUT the
dynamodb-global-tables-operator skill loaded.

---

To remove the us-west-2 replica, run:

```bash
aws dynamodb update-global-table \
  --global-table-name orders-prod \
  --replica-updates '[{"Delete":{"RegionName":"us-west-2"}}]'
```

This will remove the replica from the global table. The data in
us-west-2 will be deleted, so make sure you don't need it. After
removal, the remaining replicas will continue to function normally.

You might want to back up the data in us-west-2 before removing it.
