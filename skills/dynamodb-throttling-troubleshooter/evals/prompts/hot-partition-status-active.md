# Eval prompt: hot-partition-status-active

Diagnose the following DynamoDB throttling incident. Walk the
throttle-decision-tree and emit the standard VERDICT block (TABLE,
VERDICT, ROOT_CAUSE, THROTTLE_TYPE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A DynamoDB table `sessions-prod` in `us-east-1` is throttling on writes.
The operator already raised `WriteCapacityUnits` from 10,000 to 50,000,
but throttling persists. The application's session store is dropping
writes.

## Known facts

- `describe-table` shows:
  - `BillingMode: PROVISIONED`
  - `ProvisionedThroughput: { ReadCapacityUnits: 5000, WriteCapacityUnits: 50000 }`
  - No GSIs
  - `KeySchema: [{AttributeName: userId, KeyType: HASH}]`
- CloudWatch `ConsumedWriteCapacityUnits`: 8,000/min average — well BELOW
  the 50,000 provisioned.
- CloudWatch `ThrottledRequests`: sustained > 0 despite the 50,000 WCU
  provisioned and only 8,000 consumed.
- Contributor Insights: partition key `userId=admin` accounts for 80% of
  all write traffic.
- The application is a session store where a batch job writes ALL session
  updates under `userId=admin` for nightly aggregation. All other userId
  values account for the remaining 20% of writes.
- No GSIs exist on the table (so GSI throttling is ruled out).

## Symptom

`ProvisionedThroughputExceededException` on writes, sustained after a
5x capacity scale-up. Consumed capacity (8,000) is far below provisioned
(50,000). The root cause is the partition key distribution, not aggregate
capacity.
