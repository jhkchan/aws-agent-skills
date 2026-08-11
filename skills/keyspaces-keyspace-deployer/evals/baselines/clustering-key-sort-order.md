# Baseline (no-skill) — clustering-key-sort-order

> This is the response a model produces **without** the skill
> definition. It creates the table but misses the multi-column
> clustering key ordering (order_type ASC, order_ts DESC), the
> partition key cardinality analysis (customer_id + date =
> millions of partitions), the immutability warning (partition and
> clustering keys cannot be altered after creation), and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the table:

```bash
aws keyspaces create-table \
  --keyspace-name commerce_keyspace \
  --table-name order_history \
  --schema-definition '{"allColumns": [...], "partitionKeys": [{"name": "customer_id", "type": "uuid"}]}'
```

Add a clustering key for ordering. PITR is probably on by default.
