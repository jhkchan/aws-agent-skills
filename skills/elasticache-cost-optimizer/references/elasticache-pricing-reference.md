# Amazon ElastiCache Pricing & Decision Reference

Supplementary reference for the ElastiCache Cost Optimizer skill. Loaded
on-demand when the optimiser needs the detailed pricing matrix, Graviton
migration math, Serverless break-even calculations, replica reduction
sizing, or data-tiering cost projections.

## ElastiCache node-type pricing (us-east-1, 2026, On-Demand)

### Redis OSS — current generation (Graviton)

| Node type | vCPU | Memory | Hourly | Monthly (730h) |
|---|---|---|---|---|
| cache.r6g.large | 2 | 6.05 GB | $0.167 | $121.91 |
| cache.r6g.xlarge | 4 | 13.13 GB | $0.334 | $243.82 |
| cache.r6g.2xlarge | 8 | 26.36 GB | $0.664 | $484.72 |
| cache.r6g.4xlarge | 16 | 52.93 GB | $1.328 | $969.44 |
| cache.r6g.8xlarge | 32 | 106.21 GB | $2.656 | $1,938.88 |
| cache.r7g.large | 2 | 6.67 GB | $0.153 | $111.69 |
| cache.r7g.xlarge | 4 | 13.50 GB | $0.306 | $223.38 |
| cache.r7g.2xlarge | 8 | 27.06 GB | $0.612 | $446.76 |
| cache.r7g.4xlarge | 16 | 54.27 GB | $1.224 | $893.52 |

### Redis OSS — data-tiered (SSD-backed)

| Node type | Memory | SSD | Hourly | Monthly (730h) |
|---|---|---|---|---|
| cache.r6gd.large | 6.05 GB | 18.15 GB | $0.190 | $138.70 |
| cache.r6gd.xlarge | 13.13 GB | 39.39 GB | $0.380 | $277.40 |
| cache.r6gd.2xlarge | 26.36 GB | 79.08 GB | $0.760 | $554.80 |
| cache.r6gd.4xlarge | 52.93 GB | 158.79 GB | $1.520 | $1,109.60 |

### Redis OSS — previous generation (pre-Graviton)

| Node type | vCPU | Memory | Hourly | Monthly (730h) |
|---|---|---|---|---|
| cache.m5.large | 2 | 6.05 GB | $0.226 | $164.98 |
| cache.m5.xlarge | 4 | 13.13 GB | $0.452 | $329.96 |
| cache.m5.2xlarge | 8 | 26.36 GB | $0.904 | $659.92 |
| cache.r5.large | 2 | 6.05 GB | $0.250 | $182.50 |
| cache.r5.xlarge | 4 | 13.13 GB | $0.500 | $365.00 |
| cache.r5.2xlarge | 8 | 26.36 GB | $1.000 | $730.00 |
| cache.r4.large | 2 | 13.50 GB | $0.210 | $153.30 |
| cache.c4.large | 2 | 3.55 GB | $0.131 | $95.63 |

### Memcached — current generation

| Node type | vCPU | Memory | Hourly | Monthly (730h) |
|---|---|---|---|---|
| cache.m6g.large | 2 | 6.05 GB | $0.172 | $125.56 |
| cache.m6g.xlarge | 4 | 13.13 GB | $0.344 | $251.12 |
| cache.m6g.2xlarge | 8 | 26.36 GB | $0.688 | $502.24 |

## Graviton migration savings matrix

| Current | Target | Hourly delta | Monthly savings | % off |
|---|---|---|---|---|
| cache.m5.large | cache.r6g.large | $0.059 | $43.07 | 26% |
| cache.m5.2xlarge | cache.r6g.2xlarge | $0.240 | $175.20 | 27% |
| cache.r5.large | cache.r6g.large | $0.083 | $60.59 | 33% |
| cache.r5.2xlarge | cache.r6g.2xlarge | $0.336 | $245.28 | 34% |
| cache.r6g.large | cache.r7g.large | $0.014 | $10.22 | 8% |
| cache.r6g.2xlarge | cache.r7g.2xlarge | $0.052 | $37.96 | 8% |

Migration is a new replication group creation + data sync. No code change;
the Redis endpoint is updated via CNAME or application config.

## ElastiCache Serverless pricing

| Resource | Rate |
|---|---|
| Data (per GB-hour) | $0.00383 |
| Compute (per vCPU-hour) | $0.045 |
| Minimum data charge | 1 GB-hour |
| Snapshot storage | $0.023/GB-month |

### Serverless break-even calculation

```
provisioned_monthly = node_count × node_hourly × 730

serverless_monthly = (data_GB × $0.00383 × 730) +
                     (compute_vCPU_hours × $0.045 × 730)
```

| Provisioned node | Data (GB) | Provisioned/mo | Serverless/mo | Winner |
|---|---|---|---|---|
| cache.r6g.large (1 node) | 3 GB | $122 | $18 | Serverless |
| cache.r6g.large (1 node) | 5 GB | $122 | $30 | Serverless |
| cache.r6g.2xlarge (3 nodes) | 20 GB | $1,454 | $120 | Serverless (if idle > 50%) |
| cache.r6g.2xlarge (6 nodes) | 80 GB | $2,908 | $481 | Provisioned (steady) |
| cache.r6g.4xlarge (6 nodes) | 150 GB | $5,816 | $1,083 | Provisioned (steady) |

Rough heuristic: Serverless wins when the cluster sits below ~30% avg
utilisation. Provisioned + RN wins above ~60% steady.

## Reserved Node discount matrix

| Commitment | Payment | Discount vs On-Demand |
|---|---|---|
| 1-year | No Upfront | ~40% |
| 1-year | Partial Upfront | ~42% |
| 1-year | All Upfront | ~44% |
| 3-year | No Upfront | ~58% |
| 3-year | Partial Upfront | ~61% |
| 3-year | All Upfront | ~63% |

Redis OSS RNs are size-flexible within a family: a `cache.r6g.large` RN
covers any `cache.r6g.*` Redis node of equal or smaller size. Memcached
RNs are NOT size-flexible — tied to the specific node type.

### RN exchange

```bash
aws elasticache describe-reserved-cache-nodes-offerings \
  --cache-node-type cache.r6g.2xlarge \
  --product-description "redis" \
  --offering-type "No Upfront" --duration 31536000

aws elasticache modify-reserved-cache-nodes-offering \
  --reserved-cache-node-id <existing-rn-id> \
  --reserved-cache-nodes-offering-id <new-offering-id>
```

Exchange is within the same engine family only. No penalty; the new
offering is pro-rated from the exchange date.

## Replica reduction math

Each Redis replica is a full node billed at the same hourly rate.

```
monthly_replica_cost = replicas_per_shard × shards × node_hourly × 730
```

| Shards | Replicas/shard | Nodes | Node type | Monthly |
|---|---|---|---|---|
| 3 | 2 (primary + 2) | 9 | cache.r6g.large ($0.167) | $1,097 |
| 3 | 1 (primary + 1) | 6 | cache.r6g.large ($0.167) | $731 |
| 3 | 0 (primary only) | 3 | cache.r6g.large ($0.167) | $366 |

Reducing from 2 replicas to 1 per shard saves 33% of total node cost.
Most read-heavy workloads need only 1 replica for failover; additional
replicas are only justified when read QPS exceeds a single replica's
capacity (~100,000+ QPS for r6g.large).

## AOF vs RDB persistence cost

| Mode | Overhead | Best for |
|---|---|---|
| None | Zero | Ephemeral cache, rebuildable from DB |
| RDB (snapshots) | Periodic I/O spike; minimal steady cost | Point-in-time recovery |
| AOF (append-only) | Write amplification on every command; may force larger node | Near-zero data loss on failover |
| AOF + RDB | Both overheads; redundant | Overkill for most caches |

AOF has no separate storage charge, but the write amplification consumes
network and CPU that may force a larger node than the workload otherwise
needs. For a cache that rebuilds from a primary database on restart,
disable persistence entirely.

## Data tiering cost comparison

| Scenario | Nodes | Monthly | Per-GB effective |
|---|---|---|---|
| 6 × cache.r6g.2xlarge (158 GB total) | 6 | $2,908 | $18.40/GB |
| 3 × cache.r6gd.4xlarge (316 GB tiered) | 3 | $1,110 | $3.51/GB |
| 3 × cache.r7gd.4xlarge (326 GB tiered) | 3 | $1,016 | $3.12/GB |

Data tiering halves effective per-GB cost for datasets with a cold tail
(>50% inactive keys). For all-hot datasets, tiering adds overhead.

## Redis vs Memcached cost comparison

| Dimension | Redis OSS | Memcached |
|---|---|---|
| Replication | Yes (primary + replicas) | No (each node is independent) |
| Clustering | Yes (sharding via cluster mode) | Yes (client-side sharding) |
| Persistence | AOF, RDB | None |
| Multi-AZ | Yes (auto-failover) | No (node-level only) |
| Node size flexibility | Size-flexible RNs | Fixed RNs |
| Cost per GB | Higher (replication doubles) | Lower (no replication overhead) |
| Use case | Rich data structures, HA, persistence | Pure cache, multi-threaded |

**Rule of thumb:** Use Memcached for pure caching where HA is not
required and the dataset fits in one node. Use Redis for replication,
persistence, clustering, and rich data types. The cost difference is
driven by the replication overhead, not the per-node price.

## Pricing-region notes

Pricing above is us-east-1 baseline. Other regions vary:

- **us-west-2 / us-east-2:** ~0-5% delta
- **eu-west-1:** ~5-10% higher
- **ap-southeast-1:** ~15-20% higher
- **ap-northeast-1:** ~15-20% higher
- **sa-east-1:** ~25-30% higher

Always re-state regional rates before producing dollar estimates for
clusters outside us-east-1. Use
`https://aws.amazon.com/elasticache/pricing/` for the current matrix
filtered by region.
