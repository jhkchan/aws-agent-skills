# Baseline (no-skill) response: scan-misuse-full-table

This file captures what a generic assistant produces WITHOUT the
dynamodb-throttling-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

Your DynamoDB table is throttling on reads. Since you have 10,000 RCU
provisioned and the throttling is intermittent, it looks like something
is consuming your read capacity periodically.

The Scan operations from your dashboard are probably the cause. Scans
read the entire table, which uses a lot of read capacity. For a 50 GB
table, a Scan will use millions of RCUs.

You should raise your `ReadCapacityUnits` to handle the Scan load, or
try to make the Scan more efficient with a FilterExpression. Also
consider running the Scan less frequently, like every 30 minutes instead
of every 10 minutes.

If that does not work, switch to on-demand billing mode which handles
spiky reads better:

```bash
aws dynamodb update-table --table-name products-prod \
  --provisioned-throughput ReadCapacityUnits=30000,WriteCapacityUnits=5000
```
