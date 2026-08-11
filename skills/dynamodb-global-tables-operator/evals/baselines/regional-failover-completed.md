# Baseline (no-skill) response: regional-failover-completed

This file captures what a generic assistant produces WITHOUT the
dynamodb-global-tables-operator skill loaded.

---

Since us-east-1 is degraded, your application has correctly failed over
to us-west-2. DynamoDB Global Tables will continue replicating data
between the healthy regions.

When us-east-1 recovers, replication will resume automatically. You
should monitor for any data conflicts. Make sure your application stays
pointed at us-west-2 until us-east-1 is fully recovered.

You can check the status of your global table with:

```bash
aws dynamodb describe-global-table --global-table-name orders-prod
```

Once AWS confirms us-east-1 is healthy, you can switch back if needed.
