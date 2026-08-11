# Amazon MSK Pricing & Decision Reference

Supplementary reference for the MSK Cost Optimizer skill. Loaded
on-demand when the optimiser needs the detailed pricing matrix, Graviton
migration math, Serverless break-even calculations, broker-count
reduction sizing, or retention/storage projections.

## MSK broker-type pricing (us-east-1, 2026, On-Demand)

### Kafka 3.x — Graviton-based (m7g)

| Broker type | vCPU | Memory | Hourly | Monthly (730h) |
|---|---|---|---|---|
| kafka.m7g.large | 2 | 8 GB | $0.220 | $160.60 |
| kafka.m7g.xlarge | 4 | 16 GB | $0.440 | $321.20 |
| kafka.m7g.2xlarge | 8 | 32 GB | $0.880 | $642.40 |
| kafka.m7g.4xlarge | 16 | 64 GB | $1.760 | $1,284.80 |

### Kafka 2.8 / 3.x — previous generation (m5)

| Broker type | vCPU | Memory | Hourly | Monthly (730h) |
|---|---|---|---|---|
| kafka.m5.large | 2 | 8 GB | $0.276 | $201.48 |
| kafka.m5.xlarge | 4 | 16 GB | $0.552 | $402.96 |
| kafka.m5.2xlarge | 8 | 32 GB | $1.104 | $805.92 |
| kafka.m5.4xlarge | 16 | 64 GB | $2.208 | $1,611.84 |

### MSK Express Tier (2025+)

| Broker type | vCPU | Memory | Hourly | Monthly (730h) |
|---|---|---|---|---|
| kafka.express.m7g.large | 2 | 8 GB | $0.260 | $189.80 |
| kafka.express.m7g.2xlarge | 8 | 32 GB | $1.040 | $759.20 |

Express brokers include burst credits (baseline + burst throughput).
Cost is ~18% higher than Standard m7g but with better burst handling.

## Graviton migration savings matrix

| Current | Target | Hourly delta | Monthly savings | % off | Prerequisite |
|---|---|---|---|---|---|
| kafka.m5.large | kafka.m7g.large | $0.056 | $40.88 | 20% | Kafka 3.x+ |
| kafka.m5.2xlarge | kafka.m7g.2xlarge | $0.224 | $163.52 | 20% | Kafka 3.x+ |
| kafka.m5.4xlarge | kafka.m7g.4xlarge | $0.448 | $327.04 | 20% | Kafka 3.x+ |
| kafka.c5.large (legacy) | kafka.m7g.large | $0.046 | $33.58 | 17% | Kafka 3.x+ |

Migration requires a new MSK cluster (blue/green). Use MirrorMaker2 or
MSK Cluster Linking for topic sync. No application code change; update
the bootstrap servers in producer/consumer config.

## MSK Serverless pricing

| Resource | Rate |
|---|---|
| Partition-hour | $0.005 |
| Data stored (per GB-month) | $0.10 |
| PUT requests (per million) | $0.10 |
| GET requests | Free |

### Serverless break-even calculation

```
provisioned_monthly = broker_count × broker_hourly × 730 +
                      ebs_total_GB × $0.08

serverless_monthly = (partition_count × $0.005 × 730) +
                     (data_stored_GB × $0.10) +
                     (put_requests_millions × $0.10)
```

| Provisioned config | Ingress | Provisioned/mo | Serverless/mo | Winner |
|---|---|---|---|---|
| 3 x kafka.m5.large + 300 GB EBS | 5 MB/s | $685 | $45 | Serverless |
| 3 x kafka.m5.large + 1 TB EBS | 10 MB/s | $764 | $80 | Serverless |
| 3 x kafka.m5.large + 2 TB EBS | 30 MB/s | $844 | $220 | Serverless |
| 3 x kafka.m5.large + 2 TB EBS | 50 MB/s | $844 | $360 | Break-even |
| 3 x kafka.m5.2xlarge + 4 TB EBS | 80 MB/s | $1,626 | $600 | Provisioned |
| 6 x kafka.m5.large + 4 TB EBS | 100 MB/s | $1,570 | $750 | Provisioned |

Rough heuristic: Serverless wins below ~50 MB/s sustained ingress.
Provisioned + Graviton wins above ~50 MB/s steady.

## Broker count reduction math

Minimum 3 brokers for HA (replication factor=3). Additional brokers
are justified by throughput or partition count.

```
monthly_broker_cost = broker_count × broker_hourly × 730
```

| Brokers | Type | Monthly | Partitions/broker | Recommendation |
|---|---|---|---|---|
| 3 | kafka.m7g.large | $482 | 30 | Optimal for low throughput |
| 6 | kafka.m7g.large | $964 | 15 | Over-provisioned if ingress < 50 MB/s |
| 3 | kafka.m7g.2xlarge | $964 | 30 | Optimal for medium throughput |
| 6 | kafka.m7g.2xlarge | $1,928 | 15 | Only for high throughput > 100 MB/s |

Reducing from 6 to 3 brokers saves 50% of compute. Requires blue/green
migration (new cluster + MirrorMaker2/Cluster Linking sync).

## EBS storage pricing

| Volume type | Rate | Notes |
|---|---|---|
| gp3 (default) | $0.08/GB-month | 3000 IOPS baseline included |
| gp2 (legacy) | $0.10/GB-month | Higher cost, no baseline IOPS |

### EBS right-sizing targets

| KafkaDataLogsDiskUsed | Volume headroom | Recommendation |
|---|---|---|
| < 30% | > 3x over-allocated | Reduce volume on next blue/green |
| 30-50% | 2-3x | Slightly over-allocated; evaluate |
| 50-70% | 1.3-2x | Well-provisioned |
| > 80% | < 1.25x | Under-provisioned; increase or enable auto-expand |
| > 90% | Critical | Immediate increase or reduce retention |

EBS volume can be increased online (`update-broker-storage`) but NOT
decreased. Decreasing requires cluster recreation.

## Log retention cost projection

Retention cost is proportional to ingress rate × retention hours.

```
storage_per_broker = (ingress_per_broker_MB_s × retention_seconds) /
                     (1024 × replication_factor_share)

monthly_ebs_cost = storage_per_broker_GB × broker_count × $0.08
```

| Ingress/broker | Retention | Storage/broker | EBS cost/mo (3 brokers) |
|---|---|---|---|
| 5 MB/s | 24h | 422 GB | $101 |
| 5 MB/s | 72h | 1,266 GB | $304 |
| 5 MB/s | 168h (7 days) | 2,953 GB | $709 |
| 10 MB/s | 24h | 844 GB | $203 |
| 10 MB/s | 168h | 5,906 GB | $1,418 |
| 20 MB/s | 24h | 1,688 GB | $405 |
| 20 MB/s | 168h | 11,813 GB | $2,835 |

Reducing retention from 168h to 24h saves ~85% of EBS storage cost.
Always confirm the data-replay requirement before shortening.

## Compacted topic storage comparison

| Workload | Time retention (7d) | Compacted | Savings |
|---|---|---|---|
| Changelog (1000 keys, 10 MB/s ingest) | ~5.9 TB | ~500 MB | 99.9% |
| Event sourcing (10K events/s, 7d) | ~5.9 TB | ~50 GB | 99% |
| Session events (append-only, no keys) | ~5.9 TB | N/A (null keys) | 0% |
| CDC stream (key=PK, latest only) | ~5.9 TB | ~2 GB | 99.9% |

Compaction works only for key-based topics. Apply `cleanup.policy=compact`
(or `compact,delete` for hybrid) on topics where only the latest value
per key matters.

## MSK Express Tier cost comparison

| Workload | Standard m7g.2xlarge x 3 | Express m7g.2xlarge x 3 | Winner |
|---|---|---|---|
| Steady 40 MB/s | $1,927/mo | $2,278/mo | Standard |
| Bursty 10-60 MB/s (avg 25) | $1,927/mo | $2,278/mo | Standard (barely) |
| Bursty 10-100 MB/s (avg 30) | $2,570/mo (need 4 brokers) | $2,278/mo | Express |

Express is for variable-throughput workloads that would otherwise require
extra brokers for burst capacity. Steady workloads are cheaper on Standard.

## MSK with KRaft overhead savings

KRaft eliminates ZooKeeper, freeing broker CPU previously spent on ZK
health checks and metadata sync. Typical savings: 5-10% of broker CPU,
which can enable a one-step broker type downsize.

| Without KRaft | With KRaft | CPU freed | Downsize candidate |
|---|---|---|---|
| kafka.m7g.2xlarge (CpuUser 55%) | kafka.m7g.2xlarge (CpuUser 48%) | 7% | Maybe to xlarge if < 40% |
| kafka.m7g.xlarge (CpuUser 50%) | kafka.m7g.xlarge (CpuUser 43%) | 7% | Maybe to large if < 35% |

KRaft is available on Kafka 3.5+ on MSK.

## Pricing-region notes

Pricing above is us-east-1 baseline. Other regions vary:

- **us-west-2 / us-east-2:** ~0-5% delta
- **eu-west-1:** ~5-10% higher
- **ap-southeast-1:** ~15-20% higher
- **ap-northeast-1:** ~15-20% higher
- **sa-east-1:** ~25-30% higher

Always re-state regional rates before producing dollar estimates for
clusters outside us-east-1. Use
`https://aws.amazon.com/msk/pricing/` for the current matrix
filtered by region.
