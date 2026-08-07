# RDS and Aurora Instance Pricing Reference

Supplementary reference for the RDS Cost Optimizer skill. Loaded on-demand
when right-sizing needs the detailed instance-class pricing, engine cost
comparison, or RI discount matrix.

## RDS instance classes (us-east-1, 2026, On-Demand)

### General purpose (balanced CPU / memory)

| Instance class | vCPU | Memory | x86 $/hr | Graviton $/hr | Graviton savings |
|---|---|---|---|---|---|
| db.m6i.large | 2 | 8 GB | $0.38 | — | — |
| db.m6g.large | 2 | 8 GB | — | $0.30 | 21% |
| db.m6i.xlarge | 4 | 16 GB | $0.76 | — | — |
| db.m6g.xlarge | 4 | 16 GB | — | $0.60 | 21% |
| db.m6i.2xlarge | 8 | 32 GB | $1.52 | — | — |
| db.m6g.2xlarge | 8 | 32 GB | — | $1.20 | 21% |
| db.m6i.4xlarge | 16 | 64 GB | $3.04 | — | — |
| db.m6g.4xlarge | 16 | 64 GB | — | $2.40 | 21% |

### Memory optimized (OLTP, in-memory caches)

| Instance class | vCPU | Memory | x86 $/hr | Graviton $/hr | Graviton savings |
|---|---|---|---|---|---|
| db.r6i.large | 2 | 16 GB | $0.50 | — | — |
| db.r6g.large | 2 | 16 GB | — | $0.40 | 20% |
| db.r6i.xlarge | 4 | 32 GB | $1.00 | — | — |
| db.r6g.xlarge | 4 | 32 GB | — | $0.80 | 20% |
| db.r6i.2xlarge | 8 | 64 GB | $2.00 | — | — |
| db.r6g.2xlarge | 8 | 64 GB | — | $1.60 | 20% |
| db.r6i.4xlarge | 16 | 128 GB | $4.00 | — | — |
| db.r6g.4xlarge | 16 | 128 GB | — | $3.20 | 20% |

### Burstable (dev/test, low baseline load)

| Instance class | vCPU | Memory | $/hr | CPU credit | Notes |
|---|---|---|---|---|---|
| db.t4g.micro | 2 | 1 GB | $0.028 | Burstable | Graviton; cheapest RDS |
| db.t4g.small | 2 | 2 GB | $0.056 | Burstable | Graviton |
| db.t4g.medium | 2 | 4 GB | $0.112 | Burstable | Graviton |
| db.t4g.large | 2 | 8 GB | $0.224 | Burstable | Graviton |
| db.t3.medium | 2 | 4 GB | $0.116 | Burstable | x86; legacy |
| db.t3.large | 2 | 8 GB | $0.232 | Burstable | x86; legacy |

### Graviton4 (8th generation, rolling out 2024-2026)

| Instance class | vCPU | Memory | $/hr | Performance vs Graviton3 |
|---|---|---|---|---|
| db.r8g.large | 2 | 16 GB | ~$0.36 | ~25% better |
| db.r8g.xlarge | 4 | 32 GB | ~$0.72 | ~25% better |
| db.r8g.2xlarge | 8 | 64 GB | ~$1.44 | ~25% better |

Graviton4 instances support PostgreSQL and MySQL only (not Oracle or SQL
Server). Always prefer Graviton for open-source engines.

## Aurora Serverless v2 ACU pricing

| Component | Rate | Notes |
|---|---|---|
| ACU-hour | $0.12/ACU-hour | Billed per ACU consumed, per second |
| Minimum ACU | 0.5 ACU | Floor cost: 0.5 × $0.12 × 730 = $43.80/month |
| Maximum ACU | 128 ACU per instance | Ceiling for scale-up under load |

**ACU cost examples (730h/month):**

| Min ACU | Max ACU | Floor cost (monthly) | At avg 4 ACU | At avg 16 ACU |
|---|---|---|---|---|
| 0.5 | 16 | $43.80 | $350.40 | $1,401.60 |
| 2 | 16 | $175.20 | $350.40 | $1,401.60 |
| 8 | 64 | $701.00 | $701.00 (billed at floor) | $1,401.60 |
| 16 | 128 | $1,401.60 | $1,401.60 (billed at floor) | $1,401.60 |

**Key insight:** at min ACU 8+, Aurora Serverless v2 costs MORE than a
fixed Aurora provisioned instance (db.r6g.large at $0.40/hr = $292/month for
2 vCPU, 16 GB). Serverless v2 only wins when min ACU is LOW and the workload
genuinely scales.

## Engine cost comparison (us-east-1, db.r6i.2xlarge equivalent)

| Engine | License model | $/hr | Multiplier vs PostgreSQL |
|---|---|---|---|
| PostgreSQL | Open-source | $2.00 | 1.0× (baseline) |
| MySQL | Open-source | $2.00 | 1.0× |
| PostgreSQL (Aurora) | Open-source | ~$2.40 (ACU-equivalent) | 1.2× |
| MySQL (Aurora) | Open-source | ~$2.40 (ACU-equivalent) | 1.2× |
| Oracle Standard | License-included | ~$4.00 | 2.0× |
| Oracle Enterprise | License-included | ~$6.00 | 3.0× |
| SQL Server Express | License-included | $2.00 | 1.0× |
| SQL Server Web | License-included | ~$2.80 | 1.4× |
| SQL Server Standard | License-included | ~$5.00 | 2.5× |
| SQL Server Enterprise | License-included | ~$9.00 | 4.5× |

**BYOL (Bring Your Own License):** Oracle and SQL Server support BYOL, which
drops the hourly rate to ~$1.40-1.60/hr (near the open-source rate) IF you
already own the licenses and have active Software Assurance. BYOL requires
rigorous license tracking — surface this as a compliance burden.

## Reserved Instance discount matrix

| RI type | Term | Offering | Discount vs On-Demand | Flexibility |
|---|---|---|---|---|
| Standard | 1-yr | No Upfront | ~40% | Fixed class + engine |
| Standard | 1-yr | All Upfront | ~42% | Fixed class + engine |
| Standard | 3-yr | No Upfront | ~55% | Fixed class + engine |
| Standard | 3-yr | All Upfront | ~60% | Fixed class + engine |
| Convertible | 1-yr | No Upfront | ~30% | Exchangeable class + engine |
| Convertible | 3-yr | No Upfront | ~45% | Exchangeable class + engine |

**IMPORTANT:** RDS does NOT support Compute Savings Plans as of 2026. The
commitment vehicle is Reserved Instances only. Compute Savings Plans apply
to EC2, Fargate, and Lambda — NOT RDS.

## Storage pricing (us-east-1, 2026)

| Storage type | $/GB-month | IOPS cost | Throughput cost | Notes |
|---|---|---|---|---|
| gp3 (default) | $0.08 | Free 3000 baseline; $0.005/provisioned-IOPS above | Free 125 MB/s; $0.04/MB/s above | Default for new databases |
| io2 Block Express | $0.125 | $0.10/provisioned-IOPS-month | Included | High-performance OLTP only |
| io1 (legacy) | $0.125 | $0.10/provisioned-IOPS-month | Included | Migrate to gp3 or io2 |
| standard (magnetic) | $0.10 | — | — | Legacy; do not use |

**Break-even: gp3 vs io2:**
- gp3 with 3000 IOPS (free) costs: `GB × $0.08`
- io2 with 3000 IOPS costs: `GB × $0.125 + 3000 × $0.10 = GB × $0.125 + $300/month`
- io2 is ALWAYS more expensive than gp3 for the same storage + IOPS
- Only justified when sustained IOPS > 3000 AND Performance Insights confirms
  disk-bound queries

## Multi-AZ cost impact

| Configuration | Compute cost | Storage cost | Notes |
|---|---|---|---|
| Single-AZ | 1× instance | 1× storage | Cheapest; no HA |
| Multi-AZ (RDS) | 2× instance (standby) | 1× storage (replication included) | Compute doubles; storage does not |
| Aurora (default) | Per-instance (writer + readers) | 1× storage (6 copies, 3 AZs included) | No Multi-AZ surcharge; HA is built-in |

**Cost of Multi-AZ on a db.r6i.2xlarge:**
- Single-AZ: $2.00/hr × 730 = $1,460/month
- Multi-AZ: $2.00 × 2 × 730 = $2,920/month (+$1,460/month for the standby)

For a dev/test database, disabling Multi-AZ saves the full standby cost.

## Regional pricing variance (sample regions)

| Region | RDS base multiplier | Aurora ACU $/hr | Notes |
|---|---|---|---|
| us-east-1 (N. Virginia) | 1.0× | $0.12 | Baseline |
| us-west-2 (Oregon) | 1.0× | $0.12 | Same as us-east-1 |
| eu-west-1 (Ireland) | 1.1× | $0.132 | ~10% premium |
| eu-central-1 (Frankfurt) | 1.15× | $0.138 | ~15% premium |
| ap-southeast-1 (Singapore) | 1.15× | $0.138 | ~15% premium |
| ap-southeast-2 (Sydney) | 1.2× | $0.144 | ~20% premium |
| ap-northeast-1 (Tokyo) | 1.1× | $0.132 | ~10% premium |
| ap-south-1 (Mumbai) | 1.2× | $0.144 | ~20% premium |
| sa-east-1 (São Paulo) | 1.4× | $0.168 | ~40% premium |

**Decision impact:** in high-premium regions (sa-east-1, ap-southeast-2),
right-sizing and RI savings are LARGER in absolute dollar terms. Be MORE
aggressive with right-sizing recommendations in these regions.

Always re-state the regional rate in the SAVINGS block when the database is
not in us-east-1.
