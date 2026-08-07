# Baseline (no-skill) response: hot-partition-status-active

This file captures what a generic assistant produces WITHOUT the
dynamodb-throttling-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

Your DynamoDB table is still throttling even after raising
`WriteCapacityUnits` to 50,000. Since consumed capacity is only 8,000 and
you are still throttled, this suggests a hot partition problem.

You should redesign your partition key. The `userId=admin` key is
receiving 80% of your traffic, which means all those writes are going to
a single partition. DynamoDB distributes data across partitions by
partition key, so one hot key means one hot partition.

Try adding a suffix to the partition key to spread the load, like
`userId-admin-1`, `userId-admin-2`, etc. Or use a different attribute as
the partition key that has more distinct values.

You could also try switching to on-demand billing mode, which handles
hot partitions better:

```bash
aws dynamodb update-table --table-name sessions-prod \
  --billing-mode PAY_PER_REQUEST
```
