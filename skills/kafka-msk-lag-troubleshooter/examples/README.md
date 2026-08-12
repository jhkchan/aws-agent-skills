# Example usage: kafka-msk-lag-troubleshooter

A walkthrough showing the skill diagnosing partition skew that mimics a
consumer-rate problem, demonstrating the symptom-to-layer triage, the
per-partition lag distribution analysis (RecordsLagMax vs per-partition
lag), the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the
producer-side re-keying root cause.

## Input (user prompt)

> Our payments pipeline consumer group `cg-payments-processor` on
> topic `tx-events` started falling behind at 06:00 UTC. RecordsLagMax
> climbed from 10K to 8M over 4 hours. We've been adding consumers for
> the last hour with no improvement — please help us find the actual
> root cause.

```text
ClusterArn: arn:aws:kafka:us-east-1:111111111111:cluster/prod-msk/abc-123
ClusterType: PROVISIONED (3 brokers, kafka.m5.xlarge)
Topic: tx-events
Partitions: 12
ReplicationFactor: 3
ConsumerGroup: cg-payments-processor
ConsumerGroupMembers: 12
ConsumerGroupState: STABLE

CloudWatch metrics (last 4 hours):
  - RecordsLagMax: 10000 → 8000000
  - BytesInPerSec: 12 MB/s (flat)
  - BytesOutPerSec: 5 MB/s (flat)
  - UnderReplicatedPartitions: 0
  - CpuUser: broker-1 35%, broker-2 38%, broker-3 33%

Per-partition lag (kafka-consumer-groups --describe):
  Partition 0-6, 8-11: LAG 2-12 each
  Partition 7:          LAG 8000000

Per-partition throughput:
  Partition 7:  9.6 MB/s (80% of traffic)
  All others:   0.1-0.3 MB/s each

Producer: keyed by device-id; one device (device-abc123) generating a burst
Consumer config: fetch.min.bytes=1 (default), fetch.max.wait.ms=500 (default)
```

## Skill output

```text
TARGET: prod-msk / tx-events / cg-payments-processor
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: RecordsLagMax is 8M but 11 of 12 partitions show near-zero lag;
  partition 7 alone holds 8M lag. Per-partition BytesInPerSec shows
  partition 7 receiving 9.6 MB/s while the other 11 average 0.2 MB/s
  each. The producer uses a device-id key; one device (device-abc123)
  is generating 80% of the traffic. The default partitioner hashes
  device-id to partition 7. Adding consumers does not help because the
  skewed partition is already assigned to one consumer and cannot be
  parallelised (Step 3).
LAYER: PARTITION_SKEW
EVIDENCE:
  - Symptom: RecordsLagMax climbing from 10K to 8M over 4 hours; the
    consumer group has 12 members on 12 partitions; only the member
    assigned to partition 7 shows lag.
  - Probe: kafka-consumer-groups --describe --group cg-payments-processor
    shows partition 7 at LAG 8.0M; all other partitions LAG < 12.
  - Probe: Per-partition throughput (client-side Micrometer) shows
    partition 7 at 9.6 MB/s; others at 0.1-0.3 MB/s.
  - Passing: BytesInPerSec cluster-wide is 12 MB/s (producer rate is
    steady, not bursting); broker CpuUser is 35-38% (no saturation);
    UnderReplicatedPartitions is 0 (ISR healthy); no rebalance events;
    consumer fetch config is default (fetch.min.bytes=1).
REMEDIATION:
  1. Re-key the producer to distribute the hot device: compound key
     "device-id + epoch-minute" so the default partitioner spreads
     the burst across partitions over time.
  2. Alternatively, implement a custom partitioner that detects hot
     keys and round-robins them.
  3. Verify after re-key: per-partition lag should equalize within
     one retention window; RecordsLagMax should drop below 100K.
CONFIRM: Before deploying the producer re-key, emit and await:
  "CONFIRM: About to deploy re-keyed producer for tx-events on prod-msk.
   This changes partition assignment for new messages. Proceed? (yes/no)"
```

## What the skill caught that a generic assistant misses

1. **Distinguished uniform lag from single-partition lag.** A generic
   assistant says "add more consumers." The skill reads the
   per-partition lag distribution and identifies that 11 of 12
   partitions are at near-zero lag while partition 7 holds 8M. Adding
   consumers does nothing because partition 7 is already assigned to
   one consumer and cannot be parallelised.

2. **Identified the producer as the root cause, not the consumer.** The
   skill traces the skew to the producer's keyed partitioning strategy
   (device-id key hashing to partition 7). The fix is on the producer
   side (re-keying), not the consumer side.

3. **Ruled out broker saturation and ISR loss.** The skill's evidence
   section confirms UnderReplicatedPartitions = 0, CpuUser < 40%, and
   no rebalance events — these are the competing explanations that a
   generic assistant might chase.

4. **Provided the specific fix (compound key), not a generic "fix the
   skew."** The skill recommends re-keying with `device-id +
   epoch-minute` to distribute the burst across partitions over time.

## Slash-command invocation

```
/aws:troubleshoot-kafka-msk-lag
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why cg-payments-processor has 8M RecordsLagMax on tx-events"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: kafka-msk-lag-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the lag distribution:

```bash
# Confirm per-partition lag equalizes after re-key
# (requires client machine with kafka-consumer-groups access)
kafka-consumer-groups.sh \
  --bootstrap-server <broker-endpoint> \
  --describe --group cg-payments-processor

# Confirm RecordsLagMax drops
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name RecordsLagMax \
  --dimensions Name=Cluster,Value=prod-msk \
  --start-time $(date -u -d '-30 minutes' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum \
  --profile default --output json

# Confirm broker health remains stable
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name UnderReplicatedPartitions \
  --dimensions Name=Cluster,Value=prod-msk \
  --start-time $(date -u -d '-30 minutes' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum \
  --profile default --output json
```

Then monitor `RecordsLagMax` for 1-2 hours to confirm it drops below
100K and stabilises.
