# Baseline (no-skill) response: hot-partition-skew

This file captures what a generic assistant produces WITHOUT the
dynamodb-capacity-optimizer skill loaded.

---

You're getting throttled even though your consumed capacity is only
36-40% of what you've provisioned. This is likely because your partition
key "status" has a very uneven distribution — 80% of your items have
status "active", which means most of your traffic is hitting the same
partition.

You could increase your provisioned capacity to handle the load on that
partition. Or you could try a different partition key that distributes
traffic more evenly.

Another option is to switch to on-demand mode which handles bursts
better:

```
aws dynamodb update-table \
  --table-name tbl-hot-partition-skew \
  --billing-mode PAY_PER_REQUEST
```
