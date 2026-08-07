# Eval prompt: burst-capacity-exhaustion-spiky

Diagnose the following DynamoDB throttling incident. Walk the
throttle-decision-tree and emit the standard VERDICT block (TABLE,
VERDICT, ROOT_CAUSE, THROTTLE_TYPE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A DynamoDB table `events-ingest` in `us-east-1` throttles intermittently.
The application batches event writes every 2 minutes. For the first 5
minutes after startup, writes succeed; thereafter, every batch sees
`ProvisionedThroughputExceededException`.

## Known facts

- `describe-table` shows:
  - `BillingMode: PROVISIONED`
  - `ProvisionedThroughput: { ReadCapacityUnits: 1000, WriteCapacityUnits: 5000 }`
  - No GSIs
  - `KeySchema: [{AttributeName: eventId, KeyType: HASH}]`
- CloudWatch `ConsumedWriteCapacityUnits` at 1-minute period: alternating
  0 and 12,000 datapoints. Each batch writes ~12,000 WCU in a 10-second
  burst, then 0 for the next ~110 seconds.
- CloudWatch `ConsumedWriteCapacityUnits` at 5-minute averaging: 4,000
  WCU/min average — BELOW the 5,000 provisioned.
- CloudWatch `ThrottledRequests`: starts at minute 5 after the first
  batch, continues on every subsequent batch. No throttles in the first
  5 minutes.
- Contributor Insights: no dominant partition key — `eventId` is a UUID
  with even distribution.
- The traffic pattern is confirmed spiky with no sustained component.

## Symptom

Intermittent `ProvisionedThroughputExceededException` that begins 5
minutes after the first write batch. The 5-minute average consumed
capacity (4,000) is below provisioned (5,000), which would misleadingly
suggest capacity is sufficient. The 1-minute view reveals the spiky
pattern. The burst budget (5 minutes of unused capacity) is exhausted
after 2-3 batches, and subsequent batches throttle.
