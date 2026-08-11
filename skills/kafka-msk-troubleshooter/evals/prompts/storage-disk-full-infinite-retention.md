# Eval prompt: storage-disk-full-infinite-retention

Diagnose the following Amazon MSK cluster issue. Walk the STORAGE
diagnostic tree and emit the standard VERDICT block.

## Scenario

An Amazon MSK provisioned cluster
`prod-msk-storage-disk-full-infinite-retention` in us-east-1. DiskUsage
at 95% on all brokers. Brokers intermittently entering read-only mode.

## Known facts

- CloudWatch `AWS/Kafka` `DiskUsage`: all 3 brokers at 90-95% and
  climbing over the past 7 days.
- Broker volume size: 100 GB each (`BrokerVolumeSizeGB: 100`).
- `kafka-log-dirs --describe --topic-list <all-topics>`: each broker has
  ~95 GB of data on a 100 GB volume. Data has been accumulating for 6
  months with no cleanup.
- `aws kafka describe-configuration` shows:
  - `log.retention.hours=-1` (infinite retention)
  - `log.retention.bytes=-1` (not set / infinite)
- `aws kafka describe-cluster` shows `State: HEALTH_ISSUE`.
- `kafka-topics --describe --under-replicated-partitions` shows 5 URP
  (secondary to disk pressure causing broker slowness).
- Producers getting `NOT_ENOUGH_REPLICAS` errors intermittently.

## Symptom

All broker disks near full. Broakers entering read-only mode. Produce
failures from insufficient in-sync replicas.
