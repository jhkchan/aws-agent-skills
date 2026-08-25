# Diagnostic commands — kafka-msk-lag-troubleshooter

Pre-flight and per-step probe commands, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Account-wide pre-flight commands (moved from SKILL.md)

```bash
# 1. Cluster description (broker count, version, broker type, mode)
aws kafka describe-cluster-v2 \
  --cluster-arn <arn> --output json

# 2. Consumer group description (members, state, partition assignment)
aws kafka describe-consumer-group \
  --cluster-arn <arn> \
  --consumer-group-id <group> \
  --region <region> --output json

# 3. Topic summary (partition count, replication factor, ISR)
aws kafka describe-topic \
  --cluster-arn <arn> \
  --topic-arn <topic-arn> --output json 2>/dev/null || \
  echo "Use kafka-consumer-groups.sh via client machine for partition-level detail"

# 4. CloudWatch: aggregate lag and throughput (5-min periods)
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name RecordsLagMax \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum,Average --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name BytesInPerSec \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum,Average --output json

# 5. CloudWatch: broker saturation (per-broker CPU, disk, network)
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name CpuUser \
  --dimensions Name=Cluster,Value=<cluster-name> Name=Broker,Value=<broker-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# 6. CloudWatch: ISR and replication health
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name UnderReplicatedPartitions \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name BytesOutPerSec \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json
```

## Step 2: Consumer rate — throughput probes (moved from SKILL.md)

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name BytesOutPerSec \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json
```

If BytesInPerSec (consumer read rate) is consistently below
BytesInPerSec (producer write rate), the consumer cannot keep up.
Two sub-causes:

## Step 2a: Consumer processing-bound (moved from SKILL.md)

Each `poll()` returns records; the consumer processes them
synchronously; if processing time per record exceeds the inter-arrival
time, lag grows. Check:

```bash
# Consumer-side metrics (if Dropwizard / Micrometer exposed)
# records-consumed-rate vs records-lag-max
# Consumer fetch metrics via client JMX or CloudWatch:
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name ConsumedReadThroughput \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json
```

## Step 2a: Processing-bound remediation (moved from SKILL.md)

If consumers are processing-bound (high CPU, slow downstream DB write),
the fix is to add consumers (if partitions > current members) or
optimize the processing path (batch DB writes, async I/O).

## Step 2b: Consumer fetch-bound (micro-batch stall) (moved from SKILL.md)

If consumers are NOT CPU-bound but still cannot keep up, the fetch
config may be introducing artificial latency. Check the consumer
config:

```bash
# From the consumer application config or describe-configs on the client
# (requires kafka-configs.sh access to the cluster)
# Key properties to inspect:
#   fetch.min.bytes       (default 1)
#   fetch.max.wait.ms     (default 500)
#   max.poll.records      (default 500)
#   fetch.max.bytes       (default 57671680 = 55 MB)
```

## Step 3: Partition skew — probes (moved from SKILL.md)

```bash
# Per-partition lag (requires client machine with kafka-consumer-groups)
# kafka-consumer-groups.sh --bootstrap-server <b> --describe --group <g>
#
# CloudWatch: per-partition BytesInPerSec is not directly exposed;
# use the topic-level metric and infer from consumer-side per-partition
# records-lag-max (Micrometer/Dropwizard on the consumer).
```

## Step 4: ISR shrink — URP and offline partition probes (moved from SKILL.md)

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name UnderReplicatedPartitions \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name OfflinePartitions \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum --output json
```

## Step 4: Broker disk I/O probes (moved from SKILL.md)

```bash
# Broker disk usage (the #1 cause of ISR shrink)
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name DiskKBReadPerSec \
  --dimensions Name=Cluster,Value=<cluster-name> Name=Broker,Value=<broker-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name DiskKBWrttnPerSec \
  --dimensions Name=Cluster,Value=<cluster-name> Name=Broker,Value=<broker-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json
```

## Step 5: Broker saturation probes (moved from SKILL.md)

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name CpuUser \
  --dimensions Name=Cluster,Value=<cluster-name> Name=Broker,Value=<broker-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name NetworkProcessorAvgIdlePercent \
  --dimensions Name=Cluster,Value=<cluster-name> Name=Broker,Value=<broker-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Minimum --output json
```

## Step 7: Partition count vs group members (moved from SKILL.md)

```bash
# Topic partition count
aws kafka describe-topic --cluster-arn <arn> \
  --topic-arn <topic-arn> --output json | \
  jq '.TopicInfo.PartitionCount'

# Consumer group members
aws kafka describe-consumer-group \
  --cluster-arn <arn> \
  --consumer-group-id <group> --output json | \
  jq '.ConsumerGroupDescription.Members | length'
```

## Step 8: MSK Connect lag probes (moved from SKILL.md)

```bash
# MSK Connect connector state and lag
aws kafkaconnect describe-connector \
  --connector-arn <arn> --output json

aws cloudwatch get-metric-statistics --namespace AWS/MSKConnect \
  --metric-name RecordLag \
  --dimensions Name=ConnectorName,Value=<connector-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum,Average --output json

aws cloudwatch get-metric-statistics --namespace AWS/MSKConnect \
  --metric-name SinkTaskRecordSendRate \
  --dimensions Name=ConnectorName,Value=<connector-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json
```

## Step 9: Serverless throttle probes (moved from SKILL.md)

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name Throttle \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name ConsumedReadThroughput \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

## Step 10: Rebalance rate probe (moved from SKILL.md)

```bash
# Rebalance rate (if exposed via client metrics or CloudWatch)
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name RebalanceRate \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

## Step 11: ZooKeeper probes (moved from SKILL.md)

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name ZooKeeperRequestLatencyMs \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name SessionExpireCount \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum --output json
```
