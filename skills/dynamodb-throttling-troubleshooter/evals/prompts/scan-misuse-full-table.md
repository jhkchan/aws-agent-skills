# Eval prompt: scan-misuse-full-table

Diagnose the following DynamoDB throttling incident. Walk the
throttle-decision-tree and emit the standard VERDICT block (TABLE,
VERDICT, ROOT_CAUSE, THROTTLE_TYPE, EVIDENCE, ROOT_CAUSE_CATALOG,
REMEDIATION).

## Scenario

A DynamoDB table `products-prod` in `us-east-1` (50 GB) throttles on
reads periodically. The application's product-detail `GetItem` calls fail
intermittently with `ProvisionedThroughputExceededException`. The
operations team has noticed the throttle spikes correlate with a
dashboard report that runs every 10 minutes.

## Known facts

- `describe-table` shows:
  - `BillingMode: PROVISIONED`
  - `ProvisionedThroughput: { ReadCapacityUnits: 10000, WriteCapacityUnits: 5000 }`
  - No GSIs
  - `TableSizeBytes: ~50 GB` (~53.7 billion bytes)
  - `ItemCount: ~12,500,000`
- CloudTrail: `Scan` events every 10 minutes, correlating exactly with
  the `ThrottledRequests` spikes.
- CloudWatch `ConsumedReadCapacityUnits`: spikes to 10,000 (the full
  provisioned budget) during each Scan. Between Scans,
  `ConsumedReadCapacityUnits` is ~2,000.
- CloudWatch `ThrottledRequests`: spikes during each Scan, 0 between Scans.
- The Scan uses a `FilterExpression` that filters out 95% of scanned
  items (the filter looks for `category = "electronics"`).
- `GetItem` and `Query` traffic between Scans is well within the 10,000
  RCU provisioned capacity.
- A full Scan of the 50 GB table consumes ~6.4 million RCUs (eventually
  consistent).

## Symptom

Periodic read throttling that correlates with full-table Scan operations.
Between Scans, the table has ample capacity. The Scan consumes the entire
RCU budget for the duration of the scan (~640 seconds at 10,000 RCU/sec).
The `FilterExpression` does not reduce RCU cost — all items are read
before filtering.
