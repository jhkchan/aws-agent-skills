# Baseline (no-skill) response: gsi-backpressure-throttling

This file captures what a generic assistant produces WITHOUT the
dynamodb-throttling-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, GSI backpressure
diagnosis, composite key recommendation, throughput impact estimate).

---

Your DynamoDB table is throttling because your GSI partition key
(status) only has 3 values. Since 80% of your orders go to the
COMPLETED status, all those writes are hitting a single GSI partition,
which is causing the GSI to throttle and back-pressure your base table.

You should redesign your GSI partition key to have more distinct values.
Instead of just using `status`, you could use a composite key like
`status#date` or `status#order_type` to spread the writes across more
partitions.

You might also consider removing the GSI if it's not critical for your
query patterns, since it's causing more harm than good at this point.
