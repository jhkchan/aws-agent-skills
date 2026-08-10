# EBS Pricing and Volume Type Reference

Supplementary reference for the EBS Volume Optimizer skill. Loaded on-demand
when detailed pricing math, volume type comparison, or modification
constraints are needed.

## Volume type pricing (us-east-1, 2026, USD)

### SSD-backed volumes

| Type | $/GB-month | $/IOPS-month | $/MBps-month | Max IOPS | Max throughput | Best for |
|---|---|---|---|---|---|---|
| gp3 | $0.08 | $0.005 (above 3000) | $0.04 (above 125) | 16,000 | 1,000 MB/s | Default for most workloads |
| gp2 | $0.10 | included | included | 16,000 (burst) | varies by size | Legacy — migrate to gp3 |
| io1 | $0.125 | $0.065 | included | 64,000 | 1,000 MB/s | Mission-critical, low-latency |
| io2 | $0.125 | $0.065 | included | 64,000 (256,000 Block Express) | 4,000 MB/s | Highest durability + IOPS |

### HDD-backed volumes

| Type | $/GB-month | Max IOPS | Max throughput | Best for |
|---|---|---|---|---|
| st1 | $0.045 | 500 per TB | 500 MB/s per TB | Sequential workloads (data warehouse, log processing) |
| sc1 | $0.015 | 250 per TB | 250 MB/s per TB | Infrequently accessed data (archives, cold backups) |

### Snapshot pricing

| Tier | $/GB-month | Retrieval time | Best for |
|---|---|---|---|
| Standard | $0.05 | Instant | Active backup, DR |
| Snapshot Archive | $0.0125 | 24-72 hours | Compliance, long-term retention |
| Fast Snapshot Restore (FSR) | $0.06/hour per AZ per snapshot | Instant (pre-provisioned) | Boot volumes needing instant access |

## gp2 burst credit system

gp2 volumes earn burst credits based on their size. The baseline IOPS
(without bursting) scales linearly with volume size:

| Volume size | Baseline IOPS | Burst credits earned/hour | Max burst IOPS |
|---|---|---|---|
| 1 GB | 100 | N/A | 3000 |
| 100 GB | 300 | ~54 | 3000 |
| 250 GB | 750 | ~135 | 3000 |
| 500 GB | 1500 | ~270 | 3000 |
| 1000 GB (1 TB) | 3000 | ~540 | 3000 |
| 1667 GB | 5000 | N/A (baseline = max) | 5000 |
| 3334 GB | 10000 | N/A | 10000 |
| 5334 GB | 16000 | N/A | 16000 |

Key insight: gp2 volumes below ~1 TB have baseline IOPS < 3000 and rely
on burst credits for any I/O above baseline. Sustained I/O depletes
credits, dropping performance to the baseline level. gp3 eliminates this
by providing 3000 IOPS baseline regardless of size.

## gp3 configuration options

| Configuration | Cost | Performance |
|---|---|---|
| Baseline (free) | $0.08/GB | 3,000 IOPS + 125 MB/s |
| + 6,000 IOPS | + $0.005 × 3000 = $15/mo (for 1000 GB vol) | 6,000 IOPS + 125 MB/s |
| + 16,000 IOPS (max) | + $0.005 × 13000 = $65/mo (for 1000 GB vol) | 16,000 IOPS + 125 MB/s |
| + 250 MB/s throughput | + $0.04 × 125 = $5/mo (for any vol) | 3,000 IOPS + 250 MB/s |
| + 1,000 MB/s (max) | + $0.04 × 875 = $35/mo (for any vol) | 3,000 IOPS + 1,000 MB/s |

## io1 vs io2 comparison

| Feature | io1 | io2 |
|---|---|---|
| Durability | 99.8-99.9% | 99.999% |
| Max IOPS | 64,000 | 64,000 (256,000 Block Express) |
| Max IOPS:GB ratio | 50:1 | 500:1 |
| Multi-attach | Yes (up to 16 Nitro instances) | Yes (up to 16 Nitro instances) |
| Price | Same ($0.125/GB + $0.065/IOPS) | Same |
| Recommendation | Migrate to io2 (same price, better durability) | Default for provisioned IOPS |

## Volume modification constraints

| Modification | Online? | Downtime | Cooldown | Notes |
|---|---|---|---|---|
| Type change (e.g., gp2 → gp3) | Yes | None | One pending mod at a time | Takes 0-6 hours |
| Size increase | Yes | None | One pending mod at a time | Instant |
| Size decrease | NOT supported | N/A | N/A | Requires new volume + data copy |
| IOPS change | Yes | None | One pending mod at a time | Takes 0-6 hours |
| Throughput change (gp3) | Yes | None | One pending mod at a time | Takes 0-6 hours |

## Regional pricing multipliers

Approximate multiplier vs us-east-1 for EBS storage.

| Region | Multiplier | Notes |
|---|---|---|
| us-east-1, us-east-2, us-west-2 | 1.00x | Baseline |
| us-west-1 | 1.05x | Slight premium |
| eu-west-1, eu-west-2, eu-central-1 | 1.10-1.15x | EU premium |
| ap-southeast-1, ap-southeast-2 | 1.12-1.18x | APAC premium |
| ap-northeast-1 (Tokyo) | 1.10-1.15x | |
| ap-south-1 (Mumbai) | 1.15-1.25x | |
| sa-east-1 (São Paulo) | 1.35-1.50x | Highest premium |
| af-south-1 (Cape Town) | 1.30-1.45x | |

Always re-check via the AWS Pricing API for production estimates.

## Cost calculation worked examples

### Example 1: gp2 → gp3 (simple type migration)

```
Volume: vol-prod-web-01
Type: gp2
Size: 200 GB
Region: us-east-1

Current monthly: 200 GB × $0.10 = $20.00
Projected monthly (gp3): 200 GB × $0.08 = $16.00
Monthly saving: $4.00 (20%)
Annual saving: $48.00
```

### Example 2: io1 over-provisioned → gp3 (huge saving)

```
Volume: vol-prod-db-01
Type: io1
Size: 1000 GB
Provisioned IOPS: 20000
Consumed IOPS: 1500 (avg), 2500 (max)
Region: us-east-1

Current monthly:
  storage: 1000 × $0.125 = $125.00
  IOPS: 20000 × $0.065 = $1,300.00
  Total: $1,425.00

Projected monthly (gp3, 3000 IOPS baseline):
  storage: 1000 × $0.08 = $80.00
  IOPS: 3000 baseline (free) = $0.00
  Total: $80.00

Monthly saving: $1,345.00 (94%)
Annual saving: $16,140.00
```

### Example 3: Snapshot cleanup + Archive

```
Volume: vol-prod-app-01
Snapshots: 120 snapshots, avg 500 GB each
No DLM policy
90 snapshots older than 90 days, 0 restores in 90 days

Current monthly:
  120 × 500 GB × $0.05 = $3,000.00

Projected monthly (DLM 30-day + Archive 90):
  30 active snapshots × 500 GB × $0.05 = $750.00
  90 archived snapshots × 500 GB × $0.0125 = $562.50
  Total: $1,312.50

Monthly saving: $1,687.50 (56%)
Annual saving: $20,250.00
```

### Example 4: FSR removal

```
Snapshot: snap-prod-golden-ami (100 GB)
FSR enabled in 3 AZs
Region: us-east-1

Current monthly FSR cost:
  3 AZs × $0.06/hour × 730 hours = $131.40

Projected monthly (FSR removed):
  $0.00

Monthly saving: $131.40 (100% of FSR cost)
Note: snapshot storage ($5.00/mo) remains; only FSR is removed.
```

## Volume type selection decision tree

```
Is the workload random I/O (database, transactional)?
├── YES → Does it need > 16,000 IOPS sustained?
│   ├── YES → Does it need > 64,000 IOPS?
│   │   ├── YES → io2 Block Express (Nitro instance required)
│   │   └── NO → io2 (same price as io1, better durability)
│   └── NO → gp3 (baseline 3000 IOPS, up to 16,000 with extra cost)
└── NO (sequential, append-only, large reads) → Is it frequently accessed?
    ├── YES → st1 (Throughput Optimized HDD, $0.045/GB)
    └── NO (archive, rarely read) → sc1 (Cold HDD, $0.015/GB)
```

## Instance EBS-optimization matrix

| Instance generation | EBS-optimized by default? | Notes |
|---|---|---|
| m5, c5, r5 and later | YES (free) | All current-gen include EBS optimization |
| m4.16xlarge | YES (free) | Exception among m4 |
| m4 (except 16xlarge) | YES (paid extra) | Charges hourly for EBS-optimized |
| c4.10xlarge | YES (free) | Exception among c4 |
| c4 (except 10xlarge) | YES (paid extra) | Charges hourly |
| m3, c3 | NO | Legacy — migrate to current-gen |

Migrating from legacy (m3/c3/m4/c4) to current-gen (m5+/c5+/r5+) unlocks
free EBS optimization in addition to compute savings.
