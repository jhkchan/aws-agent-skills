# Amazon Aurora Pricing & Decision Reference

Supplementary reference for the Aurora Cost Optimizer skill. Loaded
on-demand when the optimiser needs the detailed pricing matrix, ACU
tuning math, I/O-Optimized break-even calculations, Global Database
replica sizing, or backtrack storage projections.

## Aurora instance-class pricing (us-east-1, 2026, On-Demand)

### Aurora Standard (provisioned) — Aurora PostgreSQL / MySQL

| Instance class | vCPU | Memory | Hourly | Monthly (730h) |
|---|---|---|---|---|
| db.t4g.medium | 2 | 4 GB | $0.116 | $84.68 |
| db.t4g.large | 2 | 8 GB | $0.232 | $169.36 |
| db.r6g.large | 2 | 16 GB | $0.290 | $211.70 |
| db.r6g.xlarge | 4 | 32 GB | $0.580 | $423.40 |
| db.r6g.2xlarge | 8 | 64 GB | $1.160 | $846.80 |
| db.r6g.4xlarge | 16 | 128 GB | $2.320 | $1,693.60 |
| db.r6g.8xlarge | 32 | 256 GB | $4.640 | $3,387.20 |
| db.r7g.large | 2 | 16 GB | $0.295 | $215.35 |
| db.r7g.xlarge | 4 | 32 GB | $0.590 | $430.70 |
| db.r7g.2xlarge | 8 | 64 GB | $1.180 | $861.40 |
| db.r7g.4xlarge | 16 | 128 GB | $2.360 | $1,722.80 |
| db.x2g.large | 2 | 32 GB | $0.418 | $305.14 |
| db.x2g.2xlarge | 4 | 64 GB | $0.836 | $610.28 |
| db.x2g.4xlarge | 8 | 128 GB | $1.672 | $1,220.56 |

### Aurora Serverless v2 — ACU-hourly

| Resource | Hourly | Monthly (730h) |
|---|---|---|
| 1 ACU | $0.12 | $87.60 |
| 2 ACU (typical MinCapacity) | $0.24 | $175.20 |
| 4 ACU | $0.48 | $350.40 |
| 8 ACU | $0.96 | $700.80 |
| 16 ACU | $1.92 | $1,401.60 |
| 32 ACU (typical MaxCapacity ceiling) | $3.84 | $2,803.20 |

1 ACU ≈ 2 vCPU / 16 GB RAM. The cluster bills at the ACU value
averaged per hour between MinCapacity and MaxCapacity.

### Aurora Storage pricing

| Tier | Storage per GB-month | I/O per million requests |
|---|---|---|
| Aurora Standard | $0.10 | $0.20 |
| Aurora I/O-Optimized | $0.18 | $0 (included) |

**I/O-Optimized break-even formula:**

```
break_even_IO_millions = storage_GB × ($0.18 - $0.10) / $0.20
                      = storage_GB × 0.4
```

| Storage (GB) | Break-even I/O (M/month) |
|---|---|
| 100 | 40 |
| 500 | 200 |
| 1,000 | 400 |
| 5,000 | 2,000 |
| 10,000 | 4,000 |

If actual I/O exceeds break-even, I/O-Optimized is cheaper.

### Aurora Backup pricing

| Resource | Rate |
|---|---|
| Automated backup retention (up to 100% of DB size) | Free |
| Additional backup storage (> DB size) | $0.095/GB-month |
| Manual snapshots | $0.095/GB-month |
| Backtrack change log | $0.018/GB-month (MySQL only) |
| Cross-region automated backup | $0.015/GB-month transfer + target-region storage |

### Aurora Global Database

| Component | Cost |
|---|---|
| Primary cluster storage replication | Free (storage billed at primary region) |
| Secondary-region storage | Billed at secondary region's Aurora storage rate |
| Secondary-region read replicas | Full Aurora instance-hour at secondary region's rate |
| Cross-region replication traffic | Free (Aurora storage-layer replication) |

### Aurora Data Transfer

| Pattern | Rate |
|---|---|
| Same-AZ EC2 ↔ Aurora | Free |
| Cross-AZ EC2 ↔ Aurora | $0.01/GB each direction |
| Aurora Multi-AZ replication (storage layer) | Free |
| Aurora read replica within region | Free replication |
| Cross-region Aurora Global DB replication | Free (storage layer) |

## Aurora Serverless v2 ACU tuning math

```
monthly_acu_cost = avg_acu × $0.12 × 730

floor_waste = (MinCapacity − workload_min) × $0.12 × 730
```

### Tuning targets

| Workload pattern | MinCapacity | MaxCapacity |
|---|---|---|
| Dev / test with auto-pause | 0 | 4 |
| Low-traffic web app (warm) | 1-2 | 8 |
| Standard OLTP | 2-4 | 16 |
| High-write OLTP | 4-8 | 32 |
| Analytics reader (spiky) | 2 | 64 |

The MinCapacity floor is the dominant cost lever — it bills even at
zero load. Drop it to the lowest value that still meets the cold-start
SLA.

## Reserved Instance discount matrix

| Commitment | Payment | Discount vs On-Demand |
|---|---|---|
| 1-year | No Upfront | ~40% |
| 1-year | Partial Upfront | ~42% |
| 1-year | All Upfront | ~44% |
| 3-year | No Upfront | ~58% |
| 3-year | Partial Upfront | ~61% |
| 3-year | All Upfront | ~63% |

RIs apply to a specific instance class + engine + region. A
`db.r6g.2xlarge` Aurora PostgreSQL RI does NOT cover
`db.r6g.large` or Aurora MySQL.

## Aurora vs RDS cost comparison

| Dimension | Aurora | RDS |
|---|---|---|
| Compute (per instance-hour) | Slightly higher (~5-10%) | Lower |
| Storage (Standard) | $0.10/GB-month + $0.20/M I/O | $0.115/GB-month (gp3, included I/O) |
| Multi-AZ replication | FREE (storage-layer) | $0.01/GB cross-AZ |
| Failover time | Typically < 30s | 60-120s |
| Read replicas | Up to 15 (Aurora) | Up to 5 (RDS MySQL) / 15 (PostgreSQL) |
| Storage auto-scaling | Automatic 10-GB increments | Manual or modified-storage-threshold |
| HA architecture | Cluster endpoint (single DNS) | DNS-based failover |

**Migration trigger:** Don't migrate RDS → Aurora for compute savings
alone. Trigger for HA / reader scale / storage auto-scaling; treat
cost as a secondary benefit. The free Multi-AZ replication may net
out cheaper on high-write workloads despite the higher per-compute
rate.

## Aurora Limitless Database cost structure (2024+)

| Component | Cost driver |
|---|---|
| Shard instances (Aurora Compute) | Per-instance-hour (standard Aurora pricing) |
| Router (SLG) instance | Per-instance-hour |
| Limitless management | No additional flat fee (built into instance pricing) |
| Cross-shard queries | Compute on the routing layer |

Right-sizing shards is the dominant lever. A workload that fits in
one shard should NOT be on Limitless — the routing layer adds cost
without benefit.

## Backtrack storage projections

Backtrack stores every change to the cluster for the configured
window (default 24h). Storage cost = change volume × retention window
× $0.018/GB-month.

| Change volume (GB/day) | Window | Backtrack storage | Monthly cost |
|---|---|---|---|
| 1 | 24h | ~1 GB | ~$0.018 |
| 10 | 24h | ~10 GB | ~$0.18 |
| 100 | 24h | ~100 GB | ~$1.80 |
| 100 | 72h | ~300 GB | ~$5.40 |
| 1,000 | 24h | ~1,000 GB | ~$18.00 |
| 1,000 | 72h | ~3,000 GB | ~$54.00 |

For high-change workloads, the 24h default is usually enough for
"undo" scenarios. Extending the window multiplies the storage cost
linearly.

## Performance Insights DBLoad interpretation

DBLoad (Average Active Sessions) is the primary Aurora performance
metric. Cross-reference with the instance's vCPU count:

| DBLoad / vCPU ratio | Interpretation |
|---|---|
| < 0.5 | Idle headroom — downsize candidate |
| 0.5 - 1.0 | Healthy utilisation |
| 1.0 - 2.0 | Saturated — query tuning or upsize |
| > 2.0 | Severely saturated — query regression likely |

For an 8-vCPU `db.r6g.2xlarge`:
- DBLoad avg 1.2 = 0.15 ratio → idle; right-size candidate
- DBLoad avg 12 = 1.5 ratio → saturated; consider upsize or fix top-SQL

## Top-SQL remediation playbook

When Performance Insights identifies a top-SQL > 30% of DBLoad:

1. **Identify the SQL** via `pi describe-dimension-keys --group-by
   Group=db.sql`.
2. **Get the full statement** via `pi get-dimension-key-details`.
3. **Check for missing index**: `EXPLAIN ANALYZE <statement>` — look
   for `Seq Scan` on large tables.
4. **Add the index** in dev: `CREATE INDEX ... ON ...`.
5. **Re-run EXPLAIN** to confirm the planner picks up the index.
6. **Promote to prod** during a maintenance window.
7. **Re-measure DBLoad** after 7 days; if dropped > 25%, the cluster
   may now downsize.

A single missing index can drive a 30-50% compute saving via
downsize — making DBA work the highest-leverage cost optimisation
for query-bound Aurora clusters.

## Pricing-region notes

Pricing above is us-east-1 baseline. Other regions vary:

- **us-west-2 / us-east-2:** ~0-5% delta
- **eu-west-1:** ~5-10% higher
- **ap-southeast-1:** ~15-20% higher
- **ap-northeast-1:** ~15-20% higher
- **sa-east-1:** ~25-30% higher
- **Local Zones / Wavelength:** significantly higher

Always re-state regional rates before producing dollar estimates for
clusters outside us-east-1. Use
`https://aws.amazon.com/rds/aurora/pricing/` for the current matrix
filtered by region.
