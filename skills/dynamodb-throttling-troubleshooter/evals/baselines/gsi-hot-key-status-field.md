# Baseline (no-skill) response: gsi-hot-key-status-field

This file captures what a generic assistant produces WITHOUT the
dynamodb-throttling-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

Your DynamoDB table is throttling on writes. The error
`ProvisionedThroughputExceededException` means you are exceeding the
provisioned write capacity. You should raise the `WriteCapacityUnits` on
the table.

Since you already raised it from 10,000 to 20,000 and it did not help,
try raising it further to 50,000. You can also consider switching to
on-demand mode if the traffic is unpredictable.

Also check if your partition key is well-distributed. If all writes are
going to the same partition key, DynamoDB will throttle even if the
aggregate capacity is sufficient.

To fix this, run:

```bash
aws dynamodb update-table --table-name orders-prod \
  --provisioned-throughput ReadCapacityUnits=5000,WriteCapacityUnits=50000
```

If that does not work, switch to on-demand:

```bash
aws dynamodb update-table --table-name orders-prod \
  --billing-mode PAY_PER_REQUEST
```
