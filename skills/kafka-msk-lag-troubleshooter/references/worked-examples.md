# Worked examples — kafka-msk-lag-troubleshooter

Secondary worked examples, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Worked example — ISR shrink from broker disk saturation (moved from SKILL.md)

```text
TARGET: prod-msk / tx-events / cg-payments-processor
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: UnderReplicatedPartitions is 14 (sustained for 2 hours);
  ISRShrink events correlate with broker-2 disk usage hitting 92%.
  Broker-2 cannot fetch replicas fast enough; replicas are removed
  from ISR for 14 partitions. With min.insync.replicas=2 and acks=all,
  the producer receives intermittent NOT_ENOUGH_REPLICAS; downstream
  consumer lag is a side effect of producer write failures (Step 4).
LAYER: ISR_SHRINK
EVIDENCE:
  - Symptom: RecordsLagMax climbing; producer logs show
    NOT_ENOUGH_REPLICAS errors intermittently; consumer is healthy.
  - Probe: aws cloudwatch get-metric-statistics on
    UnderReplicatedPartitions returns Maximum=14 sustained.
  - Probe: aws cloudwatch get-metric-statistics on
    DiskKBWrttnPerSec for broker-2 shows sustained write near device
    limit; disk usage at 92%.
  - Probe: ISRShrink events correlate with broker-2 disk pressure
    window.
  - Passing: broker-1 and broker-3 CpuUser < 40%, disk < 60%;
    ZooKeeper stable; no rebalance events.
REMEDIATION:
  1. Add storage to broker-2 (MSK broker storage update):
     aws kafka update-broker-storage --cluster-arn <arn> \
       --broker-ids 2 --target-broker-ebs-volume-gib 2000 \
       --region <region>
  2. Reduce topic retention to free disk space on broker-2 while the
     storage update propagates.
  3. Verify after storage update: UnderReplicatedPartitions drops to 0;
     ISRExpand events appear; producer NOT_ENOUGH_REPLICAS stops.
CONFIRM: Before updating broker storage, emit and await operator
  approval.
```

## Worked example — Consumer fetch tuning on low-volume topic (moved from SKILL.md)

```text
TARGET: prod-msk / user-events / cg-user-svc
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: RecordsLagMax climbing on topic user-events (low-volume, ~100
  records/min). Consumer config has fetch.min.bytes=10485760 (10 MB)
  and fetch.max.wait.ms=500. The topic produces ~100 KB per second;
  the consumer waits the full 500 ms fetch.max.wait.ms every poll
  cycle, fetching only 50 KB each time. Effective poll rate is 2/sec;
  consumer cannot keep up with even modest traffic (Step 2b).
LAYER: CONSUMER_FETCH_TUNING
EVIDENCE:
  - Symptom: RecordsLagMax climbing steadily; consumer CPU is < 10%;
    downstream is fast; consumer is NOT processing-bound.
  - Probe: Consumer config shows fetch.min.bytes=10485760,
    fetch.max.wait.ms=500.
  - Probe: Client-side metric records-per-sec is ~2 poll cycles ×
    ~50 records = 100 records/sec capacity; topic produces 120
    records/sec.
  - Passing: partitions are evenly distributed (no skew); broker
    healthy; no rebalance; ISR stable.
REMEDIATION:
  1. Set fetch.min.bytes=1 (or 1024 for minor batching) for the
    low-volume topic consumer group.
  2. Set fetch.max.wait.ms=100 to reduce idle wait.
  3. Verify: records-consumed-rate should match producer rate within
    one minute; RecordsLagMax should stabilise and begin draining.
```
