# Baseline (no-skill) response: write-sharding-hot-partition

This file captures what a generic assistant produces WITHOUT the
dynamodb-throttling-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, write sharding pattern
with read-complexity warning, throughput impact estimate, CONFIRM gate).

---

Your DynamoDB table is experiencing throttling because your partition
key (user_id) has uneven write distribution. The top 1% of users are
generating 80% of writes, which means those writes are concentrated on
a few partitions.

You should consider using write sharding — adding a random suffix to
your partition key to spread writes across multiple partitions. For
example, instead of using `user123` as the partition key, you could use
`user123#01`, `user123#02`, etc.

You'll need to update your application code to:

1. Add the suffix when writing
2. Query all suffixes in parallel when reading

Also, you might want to increase your write capacity units since your
average consumption (2800/s) is close to your provisioned (3000/s).
