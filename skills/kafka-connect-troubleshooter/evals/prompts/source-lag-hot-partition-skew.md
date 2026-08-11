# Eval prompt: source-lag-hot-partition-skew

Diagnose the Kafka Connect / MSK Connect failure. Walk the nine-
category diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, CATEGORY, EVIDENCE, REMEDIATION).

Connector: events-stream-source
  (case source-lag-hot-partition-skew)
Region: us-east-1
WorkerType: MCU.2 (2 worker units)

describe-connector output:
  connector.state: RUNNING
  tasks: all RUNNING (no FAILED)

MSK consumer group lag (events-stream-source group):
  partition 0: 1,800 records lag
  partition 1: 1,500 records lag
  ...
  partition 7: 480,000 records lag  <-- hot
  ...
  partition 15: 1,200 records lag

Per-task throughput:
  task for partition 7: 5 records/s
  tasks for other partitions: ~200 records/s each

Producer config:
  partitioner: default key-based (murmur2)
  Most frequent key: "ACME-001" (60% of records)

No rebalance churn; source DB healthy; no error logs.
