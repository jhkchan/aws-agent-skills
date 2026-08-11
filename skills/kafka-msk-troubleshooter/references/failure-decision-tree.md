# MSK Failure Decision Tree — Reference

Supplementary reference for the Kafka MSK Troubleshooter skill. Walks the
full symptom-to-cause tree with worked examples per category.

## MSK cluster lifecycle and where each failure strikes

```
   cluster HEALTHY (ACTIVE, no URP)
        |
        v
   [HEALTH_ISSUE] ---- broker NOT_HEALTHY ----> [A] BROKER_FAILURE
        |                                        |-- EBS volume failure
        |                                        |-- OOM / GC thrashing
        |                                        |-- CPU saturation
        |                                        |-- MSK auto-replacing broker
        v
   [URP / ISR shrink] ---- followers behind ----> [B] TOPIC_ISSUE
        |                                             |-- broker down (secondary)
        |                                             |-- replica.lag.time.max.ms
        |                                             |-- partition skew
        |                                             |-- offline partitions (P0)
        v
   [clients cannot connect] ---- auth / network ---> [C] CONNECTIVITY
        |                                             |-- security group
        |                                             |-- TLS / SCRAM / IAM mismatch
        |                                             |-- bootstrap endpoint wrong
        |                                             |-- cross-VPC routing
        v
   [ZK session expired] ---- broker-ZK partition ----> [D] ZOOKEEPER
        |                                              |-- zookeeper.set.acl
        |                                              |-- ZK latency
        |                                              |-- KRaft mode: N/A
        v
   [config drift] ---- auto-create / retention -------> [E] CONFIGURATION
        |                                              |-- auto.create.topics
        |                                              |-- log.retention.hours=-1
        |                                              |-- num.partitions=1
        v
   [metrics absent] ---- monitoring not enabled ------> [F] MONITORING
        |                                              |-- enhanced monitoring off
        |                                              |-- Prometheus JMX down
        v
   [disk full] ---- EBS volume exhausted ------------> [G] STORAGE
                                                       |-- retention infinite
                                                       |-- compacted topic growth
                                                       |-- partition skew
```

Category letters map to the steps in SKILL.md:

- A = BROKER_FAILURE (Step 2)
- B = TOPIC_ISSUE (Step 3)
- C = CONNECTIVITY (Step 4)
- D = ZOOKEEPER (Step 5)
- E = CONFIGURATION (Step 6)
- F = MONITORING (Step 7)
- G = STORAGE (Step 8)

**Rule:** pick the EARLIEST failure as the root cause. BROKER_FAILURE
produces URP, which produces client errors. Fix the broker first.

## Category A: BROKER_FAILURE

### Worked example — EBS volume failure triggering auto-replacement

**Symptom:** cluster State=`HEALTH_ISSUE`. StateInfo:
`Broker 2 is not healthy. Replacement in progress.`

**Walk:**

1. `aws kafka describe-cluster --cluster-arn <arn>` shows
   `State: HEALTH_ISSUE`, `StateInfo: "Broker 2 is NOT_HEALTHY"`.
2. `aws kafka list-nodes --cluster-arn <arn>` shows broker 2
   `InstanceType: kafka.m5.large`, `BrokerVolumeSizeGB: 100`.
3. CloudWatch `DiskUsage` for broker 2 spiked to 100% before the broker
   went unhealthy.
4. MSK initiated automatic broker replacement (State=`MAINTENANCE`).

**Root cause:** BROKER_FAILURE — EBS volume filled to 100%, broker entered
read-only mode, MSK auto-replacing (catalog #1 + #11).

**Fix:** Wait for MSK replacement to complete. Meanwhile, fix the storage
issue (Step 8) to prevent recurrence: set finite retention and increase
EBS volume size.

### Worked example — CPU saturation causing degraded throughput

**Symptom:** producers report high latency. Cluster State=`ACTIVE`.
`CpuUser` sustained at 90%+ on broker 1.

**Walk:**

1. CloudWatch `CpuUser` broker 1: Average=92%, Maximum=98% over 4 hours.
2. `BytesInPerSec`: 85 MB/s average, spikes to 120 MB/s. Normal: 15 MB/s.
3. `kafka-topics --describe`: 60% of partition leaders are on broker 1
   (partition skew).
4. Brokers 2 and 3: `CpuUser` Average=35%.

**Root cause:** BROKER_FAILURE — CPU saturation from partition skew. Broker 1
handles 60% of produce traffic (catalog #4 + #1).

**Fix:** Run `kafka-preferred-replica-election` to rebalance leadership. For
persistent skew, run `kafka-reassign-partitions` with an even distribution.

## Category B: TOPIC_ISSUE

### Worked example — ISR flapping under burst load

**Symptom:** `UnderReplicatedPartitions` spikes to 28 during 09:00-10:00
then drops to 0 by 10:15. Repeats at 14:00-15:00.

**Walk:**

1. `kafka-topics --describe --under-replicated-partitions` shows 28
   partitions during the burst window. `Isr` is missing broker 2 and 3.
2. `describe-configuration`: `replica.lag.time.max.ms=30000` (default).
3. CloudWatch `BytesInPerSec`: spikes to 85 MB/s (baseline 12 MB/s) during
   the same windows. Followers cannot fetch fast enough within 30s.
4. After the burst subsides, followers catch up and rejoin ISR. URP=0.

**Root cause:** TOPIC_ISSUE — ISR flapping from `replica.lag.time.max.ms`
too aggressive (catalog #3).

**Fix:** Raise `replica.lag.time.max.ms` to 60000 in a new MSK configuration
revision.

### Worked example — Offline partitions (P0)

**Symptom:** `OfflinePartitions=3`. Producers get
`NOT_LEADER_OF_PARTITION` for 3 topics.

**Walk:**

1. `kafka-topics --describe --under-min-isr-partitions` shows 3 partitions
   with `Isr: ` (empty) or `Isr: 1` when min ISR is 2.
2. `aws kafka describe-cluster`: broker 2 is `NOT_HEALTHY`. Broker 2 was
   the leader for all 3 offline partitions.
3. No other broker can take over because ISR is below `min.insync.replicas`.

**Root cause:** TOPIC_ISSUE — offline partitions from broker failure +
ISR below min (catalog #2).

**Fix:** Restore broker 2 (Step 2). Once it rejoins ISR, leadership
transfers and partitions come online. If `min.insync.replicas=2` and
only 1 broker is in ISR, producers with `acks=all` are blocked until
the second broker rejoins.

## Category C: CONNECTIVITY

### Worked example — Security group blocking port 9094

**Symptom:** producer `TimeoutException` connecting to TLS bootstrap
brokers. Consumer also fails.

**Walk:**

1. `aws kafka get-bootstrap-brokers --cluster-arn <arn>` returns
   `BootstrapBrokerStringTls: b-1.xxx.kafka.us-east-1.amazonaws.com:9094,...`.
2. Client security group ID: `sg-aaa`. Broker security group: `sg-bbb`.
3. `aws ec2 describe-security-groups --group-ids sg-bbb`: inbound rule
   allows port 9092 (PLAINTEXT), NOT 9094 (TLS).
4. `telnet b-1.xxx.kafka.us-east-1.amazonaws.com 9094` times out.

**Root cause:** CONNECTIVITY — security group missing inbound on port 9094
(catalog #5).

**Fix:** Add inbound rule on `sg-bbb` for port 9094 from `sg-aaa`.

### Worked example — SCRAM secret not associated with cluster

**Symptom:** producer `SASL_AUTHENTICATION_FAILED`. Client uses
`sasl.mechanism=SCRAM-SHA-512`.

**Walk:**

1. `aws kafka describe-cluster --cluster-arn <arn>`:
   `ClientAuthentication.Sasl.Scram.Enabled: true`.
2. `aws kafka list-scram-secrets --cluster-arn <arn>` returns empty —
   no secret associated.
3. `aws secretsmanager list-secrets --filter Key=name,Values=AmazonMSK_`
   returns a secret `AmazonMSK_prod_msk_credentials` but it is not
   linked to the cluster.

**Root cause:** CONNECTIVITY — SCRAM secret exists but not associated
with the cluster (catalog #7).

**Fix:** Associate the secret:
```bash
aws kafka batch-associate-scram-secret \
  --cluster-arn <arn> \
  --secret-arn-list arn:aws:secretsmanager:us-east-1:111111111111:secret:AmazonMSK_prod_msk_credentials-XXXX
```

## Category D: ZOOKEEPER

### Worked example — ZK session expired from network partition

**Symptom:** broker logs show repeated `ZooKeeper session expired`.
Controller flapping. Cluster State=`HEALTH_ISSUE`.

**Walk:**

1. Broker CloudWatch Logs `/aws/kafka/<cluster>/broker-2`:
   `Session expired event. Initiating re-initialization.`
2. CloudWatch `ZooKeeperRequestLatencyMs` for broker 2: spikes to 5000ms
   (normal: <10ms). Other brokers: normal.
3. Broker 2 is in subnet `subnet-aaa`. ZK ENIs are in `subnet-bbb`.
   Route table for `subnet-aaa` has no route to `subnet-bbb` (route was
   deleted during a VPC reconfiguration).

**Root cause:** ZOOKEEPER — network partition between broker and ZK subnet
(catalog #9).

**Fix:** Restore the VPC route table entry for `subnet-aaa` to reach
`subnet-bbb`.

## Category E: CONFIGURATION

### Worked example — auto-create topics producing 1-partition topics

**Symptom:** new topics keep appearing with 1 partition. Partition skew
across brokers. Throughput bottlenecked on the single leader.

**Walk:**

1. `kafka-topics --list` shows topics the operator never created:
   `temp-events`, `debug-logs`, `test-queue`.
2. `kafka-topics --describe --topic temp-events`:
   `PartitionCount: 1, ReplicationFactor: 3`.
3. `describe-configuration`: `auto.create.topics.enable=true`,
   `num.partitions=1`.

**Root cause:** CONFIGURATION — auto-create enabled with default 1 partition
(catalog #10).

**Fix:** Set `auto.create.topics.enable=false`. Create topics explicitly
with the correct partition count (e.g., 6-12 for high-throughput topics).

## Category G: STORAGE

### Worked example — Disk full from infinite retention

**Symptom:** `DiskUsage=95%`. Brokers entering read-only mode. Producers
getting `RecordTooLargeException` or `NOT_ENOUGH_REPLICAS`.

**Walk:**

1. CloudWatch `DiskUsage`: all brokers at 90-95% and climbing.
2. `describe-configuration`: `log.retention.hours=-1` (infinite retention).
   `log.retention.bytes` not set (defaults to -1, also infinite).
3. `kafka-log-dirs --describe --topic-list <all-topics>`: each broker has
   ~95 GB of data on a 100 GB volume.
4. Topics have been accumulating data for 6 months with no cleanup.

**Root cause:** STORAGE — infinite retention filling EBS volumes
(catalog #11).

**Fix:**

1. Immediately: set `log.retention.hours=168` (7 days) and
   `log.retention.bytes=85899345920` (80 GB) in a new configuration revision.
2. Increase EBS volume to 500 GB: `aws kafka update-broker-storage` or
   update broker type.
3. Monitor `DiskUsage` over 24 hours as retention cleanup takes effect.

## Cross-category decision flowchart

```
START
  |
  v
Cluster State = HEALTH_ISSUE?
  |-- YES --> BROKER_FAILURE (Step 2)
  |            |-- MAINTENANCE: wait for replacement
  |            |-- CpuUser > 85%: scale up / fix partition skew
  |            |-- DiskUsage > 90%: STORAGE (Step 8)
  |
  v NO (State = ACTIVE)
kafka-topics --describe --under-replicated-partitions returns rows?
  |-- YES --> TOPIC_ISSUE (Step 3)
  |            |-- OfflinePartitions > 0: P0, fix broker
  |            |-- ISR flapping: raise replica.lag.time.max.ms
  |            |-- Partition skew: preferred-replica-election
  |
  v NO (URP = 0)
Producer/consumer connection errors?
  |-- YES --> CONNECTIVITY (Step 4)
  |            |-- TimeoutException: check SG + bootstrap endpoint
  |            |-- SASL_AUTHENTICATION_FAILED: verify auth mode + secret
  |            |-- SSLHandshakeException: verify truststore + CA cert
  |            |-- TopicAuthorizationException: check ACLs
  |
  v NO
ZooKeeper session expired? (ZK mode only)
  |-- YES --> ZOOKEEPER (Step 5)
  |            |-- Network partition: fix VPC routes
  |            |-- AUTH_FAILED: fix zookeeper.set.acl
  |
  v NO
Unknown topic errors or config drift?
  |-- YES --> CONFIGURATION (Step 6)
  |            |-- UnknownTopicOrPartitionError: disable auto-create
  |            |-- Retention not working: set finite retention
  |
  v NO
Metrics absent?
  |-- YES --> MONITORING (Step 7)
  |            |-- Enable enhanced monitoring PER_BROKER
  |            |-- Enable open monitoring for Prometheus
  |
  v NO
DiskUsage > 90%?
  |-- YES --> STORAGE (Step 8)
  |            |-- Set finite retention
  |            |-- Increase EBS volume
  |
  v
NEED_MORE_INFO -- gather more context
```
