# Eval: clustering-key-sort-order

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — composite partition key (customer_id + order_date), multi-column clustering key (order_type ASC, order_ts DESC) for range queries

## Prompt

Create a table order_history in keyspace commerce_keyspace.
Columns: customer_id (uuid), order_date (date), order_ts
(timestamp), order_type (text), amount (decimal), status (text).
Partition key: (customer_id, order_date). Clustering key:
(order_type ASC, order_ts DESC). This supports queries like "get
all returns for customer X on date Y, newest first." On-demand
capacity. PITR enabled. Region us-east-1. Tags:
Environment=production, Domain=orders.
