# Worked Examples (load on demand) — DynamoDB Throttling Troubleshooter

Secondary worked examples and CLI/code patterns, moved verbatim from SKILL.md.


---

## Worked example — burst capacity exhaustion (moved from SKILL.md)

```text
TABLE: events-ingest in us-east-1
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: BURST_EXHAUSTED — traffic is spiky (batch writes every 2
  minutes). The 5-minute burst capacity absorbs the first 2-3 batches,
  then throttling begins. Average WCU is 4,000/min (below the 5,000
  provisioned), but the peak batch is 12,000 WCU in 10 seconds.
THROTTLE_TYPE: BURST_EXHAUSTED
EVIDENCE:
  - CloudWatch ConsumedWriteCapacityUnits (1-min period): alternating
    0 and 12,000 datapoints — confirms spiky pattern
  - CloudWatch ThrottledRequests: starts ~5 minutes after the first
    batch, continues on every subsequent batch
  - CloudWatch ConsumedWriteCapacityUnits (5-min avg): 4,000 WCU/min
    — below the 5,000 provisioned, misleading if viewed at 5-min period
ROOT_CAUSE_CATALOG: #5 (burst capacity exhaustion)
REMEDIATION:
  1. Raise ProvisionedWriteCapacityUnits to the 99th percentile of the
    per-second rate, not the per-minute average:
    aws dynamodb update-table --table-name events-ingest \
      --provisioned-throughput ReadCapacityUnits=1000,WriteCapacityUnits=12000
  2. Or switch to on-demand for immediate relief:
    aws dynamodb update-table --table-name events-ingest \
      --billing-mode PAY_PER_REQUEST
  3. Or smooth the traffic: buffer batches in SQS, drain at a steady
    rate via a Lambda consumer writing to DynamoDB.
```
