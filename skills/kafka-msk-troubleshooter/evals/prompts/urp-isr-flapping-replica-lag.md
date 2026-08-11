# Eval prompt: urp-isr-flapping-replica-lag

Diagnose the following Amazon MSK cluster issue. Walk the TOPIC_ISSUE
diagnostic tree and emit the standard VERDICT block (INCIDENT, VERDICT,
ROOT_CAUSE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

An Amazon MSK provisioned cluster
`prod-msk-urp-isr-flapping-replica-lag` in us-east-1 (account
111111111111) has UnderReplicatedPartitions spiking during business
hours.

## Known facts

- `aws kafka describe-cluster` shows `State: ACTIVE`, `StateInfo: ""`
  (empty). All brokers HEALTHY.
- `kafka-topics --describe --under-replicated-partitions` shows 28
  partitions across `orders`, `payments`, `inventory` topics during burst
  windows. `Isr` is missing broker 2 and 3 (e.g.
  `Replicas: 1,2,3` / `Isr: 1`).
- CloudWatch `AWS/Kafka` metrics during burst windows (09:00-10:00,
  14:00-15:00):
  - `UnderReplicatedPartitions`: Average=12, Maximum=28
  - `BytesInPerSec`: spikes to 85 MB/s (baseline: 12 MB/s)
  - `CpuUser` (all brokers): 40-55% (normal range)
- After the burst subsides (~10-15 minutes), followers catch up and
  rejoin ISR. `UnderReplicatedPartitions` drops to 0.
- `aws kafka describe-configuration` shows:
  `replica.lag.time.max.ms=30000` (default, unchanged)

## Symptom

Under-replicated partitions spike during produce bursts and self-resolve
within minutes, causing brief windows of degraded replication.
