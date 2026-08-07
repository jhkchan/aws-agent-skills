# Eval prompt: gsi-hot-key-status-field

Diagnose the following DynamoDB throttling incident. Walk the
throttle-decision-tree and emit the standard VERDICT block (TABLE,
VERDICT, ROOT_CAUSE, THROTTLE_TYPE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A DynamoDB table `orders-prod` in `us-east-1` is returning
`ProvisionedThroughputExceededException` on `PutItem` calls. The
application's checkout service is failing order writes.

## Known facts

- `describe-table` shows:
  - `BillingMode: PROVISIONED`
  - `ProvisionedThroughput: { ReadCapacityUnits: 5000, WriteCapacityUnits: 10000 }`
  - One GSI: `status-index` with `KeySchema: [{AttributeName: status, KeyType: HASH}]`
  - GSI `ProvisionedThroughput: { ReadCapacityUnits: 5000, WriteCapacityUnits: 10000 }`
- CloudWatch `ThrottledRequests` (base table, Operation: PutItem): sustained
  > 0 for the last 30 minutes.
- CloudWatch `ConsumedWriteCapacityUnits` (base table): 8,000/min average,
  BELOW the 10,000 provisioned.
- CloudWatch `ThrottledRequests` (GSI status-index): sustained > 0,
  correlated with the base table throttles.
- CloudWatch `ConsumedWriteCapacityUnits` (GSI status-index): at the GSI
  provisioned limit of 10,000.
- Contributor Insights: top GSI key `status=ACTIVE` accounts for 60% of
  GSI traffic.
- The `status` attribute has only 4 distinct values: PENDING, ACTIVE,
  SHIPPED, DELIVERED.
- The operator already raised base table `WriteCapacityUnits` from 10,000
  to 20,000 — throttling persisted.

## Symptom

`ProvisionedThroughputExceededException` on base-table `PutItem` calls,
sustained for 30 minutes. Base table consumed capacity is below provisioned.
The GSI is throttling and propagating to the base table write path.
