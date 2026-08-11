# Eval prompt: gsi-projection-bloat

Optimise the following DynamoDB table for cost. Walk the GSI optimization
analysis and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

TableName: tbl-gsi-projection-bloat
Region: us-east-1
BillingMode: PAY_PER_REQUEST
GSIs: 3
  - gsi-by-status: projection=ALL, size=120 GB
  - gsi-by-category: projection=ALL, size=95 GB
  - gsi-by-date: projection=ALL, size=85 GB
  (Total GSI storage: 300 GB)
Base table storage: 200 GB, avg item size 8 KB
TTL: not enabled
Table Class: STANDARD
Streams: NEW_IMAGES
Metrics (last 30 days):
  - ConsumedReadCapacityUnits: avg 2000/s
  - ConsumedWriteCapacityUnits: avg 800/s
  - GSI queries: gsi-by-status 5000/d, gsi-by-category 200/d, gsi-by-date 50/d

Workload context: e-commerce order table. gsi-by-status is heavily
queried (order status lookups) and needs 5 attributes (status, total,
customer_id, created_at, tracking_number). gsi-by-category and
gsi-by-date are rarely queried and only need partition + sort key.
All GSIs use ALL projection unnecessarily.
