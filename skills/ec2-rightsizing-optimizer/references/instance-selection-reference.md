# EC2 Instance Selection Reference Guide

Supplementary reference for the EC2 Rightsizing Optimizer skill. Loaded
on-demand when family selection needs the detailed spec table, Graviton
compatibility matrix, or pricing-model decision logic.

## Current-generation instance families (2026)

### General purpose

| Family | Processor | Use case | vCPU-to-memory ratio | Notable |
|---|---|---|---|---|
| m7i | Intel Sapphire Rapids | Web/app, dev/test, small DB | 1:4 | DDR5; default for new x86 workloads |
| m7a | AMD Genoa | Same as m7i | 1:4 | AMD alternative for cost-conscious |
| m7g | Graviton 3 | Same as m7i (ARM-compatible) | 1:4 | Up to 20% cheaper than m7i |
| m7i-flex | Intel (flex) | Web-tier cost optimization | 1:4 | Lower baseline network; cheaper |
| m7gd | Graviton 3 + local NVMe | General + local storage | 1:4 | Local NVMe for cache/temp |
| m6i, m6a, m6g | Prior gen | Same | 1:4 | Still valid; m7 preferred for new |
| m5, m5a, m5n, m5dn | Legacy (Skylake) | Existing fleets | 1:4 | Migrate to m7 for free perf bump |
| t3, t3a, t4g | Burstable | Dev/test, low-traffic | 1:4 | CPU credit system |

### Compute optimized

| Family | Processor | Use case | vCPU-to-memory ratio | Notable |
|---|---|---|---|---|
| c7i, c7i-flex | Intel Sapphire Rapids | Batch, HPC, web servers, CI | 1:2 | Highest vCPU/$ for x86 |
| c7a | AMD Genoa | Same as c7i | 1:2 | AMD alternative |
| c7g, c7gd | Graviton 3 | Same (ARM) | 1:2 | Best price-performance for ARM-compatible compute |
| c6n | Intel (network) | HFT, NFV, real-time streaming | 1:2.5 | 100 Gbps networking |
| c6id, c6idn | Intel + local NVMe | Compute + local storage | 1:2 | NVMe for NoSQL on compute nodes |
| c6i, c6a, c6g | Prior gen | Same | 1:2 | Still valid; c7 preferred for new |
| c5, c5a, c5n, c5d | Legacy (Skylake) | Existing fleets | 1:2 | Migrate to c7 for perf bump |

### Memory optimized

| Family | Processor | Use case | vCPU-to-memory ratio | Notable |
|---|---|---|---|---|
| r7i, r7a | Intel / AMD | In-memory cache (Redis), relational DB | 1:8 | DDR5; better network than r6 |
| r7g, r7gd | Graviton 3 | Same (ARM) | 1:8 | Best price-performance for ARM DB |
| r6in, r6idn | Intel (network) | Memory + network workloads | 1:8 | 100 Gbps networking |
| r6i, r6a, r6g | Prior gen | Same | 1:8 | Still valid; r7 preferred for new |
| r5, r5a, r5n, r5dn, r5b | Legacy (Skylake) | Existing fleets | 1:8 | r5b: EBS-optimized for max IOPS |
| x2idn, x2iedn, x2iezn | Intel (extreme) | SAP HANA, large analytics | 1:12 to 1:48 | Very high memory; tier-1 enterprise |
| x2gd | Graviton 2 (extreme) | Same (ARM) | 1:12 | ARM alternative for extreme memory |

### Storage optimized

| Family | Processor | Use case | vCPU-to-memory ratio | Notable |
|---|---|---|---|---|
| i8g | Graviton 4 (2024-2025) | NoSQL (Cassandra, MongoDB), data warehouse | 1:8 | NVMe + ARM; new in 2024 |
| i4i, i4g | Intel / Graviton 3 | Same | 1:8 | NVMe local storage; OLAP/OLTP |
| im4gn | Graviton 2 | Same (ARM) | 1:8 | Lower-cost Graviton option |
| d3, d3en | Intel | Hadoop, data lake | 1:5 | HDD-based instance storage |
| hpc7g | Graviton 3 | HPC workloads | 1:8 | EFA fabric; HPC-optimized |

### GPU / accelerator

| Family | Accelerator | Use case | Notable |
|---|---|---|---|
| p5 | NVIDIA H100 | ML training (LLM, large models) | Highest GPU perf; premium price |
| p4d, p4de | NVIDIA A100 | ML training, HPC | Prior gen; still widely used |
| p3, p3dn | NVIDIA V100 | Legacy ML training | Migrate to p5 or trn1 |
| g5, g5g | NVIDIA A10G / T4G | ML inference, rendering | Cost-effective inference |
| g6, g6e | NVIDIA L4 | ML inference, video encoding | Newer than g5; better perf/$ |
| inf2 | AWS Inferentia2 | ML inference (transformer models) | Cost-effective for large inference |
| trn1, trn1n | AWS Trainium | ML training | AWS chip; lower cost than p4/p5 for many models |
| dl1 | Habana Gaudi | ML training (alternative) | Limited deployment |

### Network optimized

| Family | Network | Use case |
|---|---|---|
| c6n, m6n, r6n | 100 Gbps | HFT, NFV, real-time streaming |
| c7gn | Graviton 3 + 100 Gbps | Network + ARM compute |
| p4de | 400 Gbps (EFA) | Distributed ML training |

## Graviton (ARM) compatibility matrix

### Workloads with full Graviton support

| Runtime | Status | Notes |
|---|---|---|
| Java 11+ (OpenJDK, Amazon Corretto) | Full | JIT, GC work unchanged |
| Python 3.8+ | Full | Most C-extension packages have arm64 wheels (2024+) |
| Go 1.16+ | Full | Cross-compile via `GOOS=linux GOARCH=arm64` |
| Node.js 16+ | Full | Verify native addons have arm64 builds |
| Ruby 3.0+ | Full | Verify gems with native extensions |
| .NET 6+ | Full | Microsoft ARM64 support mature |
| Rust (stable) | Full | Recompile for aarch64 |
| Containerized workloads (Docker, containerd) | Full | Use multi-arch images or arm64-only |

### Workloads requiring recompile or verification

| Runtime | Action | Notes |
|---|---|---|
| C/C++ | Recompile for aarch64 | Check all dependencies for ARM builds |
| Native libraries (.so files) | Replace with arm64 builds | Common offender: legacy JNI, proprietary DB drivers |
| Container images with single-arch x86 | Rebuild via `docker buildx` | Multi-arch manifest list recommended |
| Lambda functions with custom runtime | Recompile / use arm64 build | Lambda supports graviton (aws lambda update-function-configuration --architectures arm64) |

### Workloads NOT Graviton-compatible

| Runtime | Reason | Mitigation |
|---|---|---|
| x86 assembly in C/C++ | Architecture-specific | Rewrite or stay x86 |
| Proprietary software with x86-only builds | Vendor lacks ARM build | Engage vendor; stay x86 |
| Some legacy Windows Server workloads | Windows on ARM less mature | Stay x86 until app modernization |
| Workloads using Intel MKL, AVX-512 intrinsics | Architecture-specific | Rewrite against portable libraries (OpenBLAS) |

## Pricing model decision matrix

### Selection criteria

| Pattern | Recommended | Alternative |
|---|---|---|
| Steady-state 24/7, no growth uncertainty | 3-yr Standard RI (Regional) | 3-yr Compute Savings Plan |
| Steady-state with growth | 3-yr Convertible RI | 3-yr Compute Savings Plan |
| Steady-state, uncertain 1-year horizon | 1-yr Compute Savings Plan | 1-yr Convertible RI |
| Dev/test, business-hours | 1-yr Convertible RI | Scheduled RI (limited) |
| Batch, fault-tolerant, horizontally scaled | Spot Instances | On-Demand for overflow |
| Mixed fleet, some steady / some variable | Compute Savings Plan for baseline + On-Demand/Spot for variable | Per-instance RIs |
| Short-lived experiments | On-Demand | — |
| Mission-critical, no interruption tolerance | Standard RI (3-yr) | — |

### Discount table (approximate, us-east-1, 2026)

| Model | 1-yr commitment | 3-yr commitment |
|---|---|---|
| Standard RI | ~40% off On-Demand | ~60% off On-Demand |
| Convertible RI | ~30% off | ~55% off |
| Compute Savings Plan | ~30% off | ~50% off |
| Instance Savings Plan | ~35% off | ~55% off |
| Spot | Up to 90% off (interruptible) | — |

### Commitment laddering (recommended approach)

1. **Week 0**: Identify steady-state compute spend via Cost Explorer.
   Commit to a 1-yr Compute Savings Plan for this baseline.
2. **Day 30**: After observing additional workload patterns, extend
   commitment to 3-yr Compute Savings Plan or Convertible RI for deeper
   discount.
3. **Day 60**: Add Spot for batch / fault-tolerant workloads.
4. **Quarterly**: Re-evaluate based on workload growth, new instance
   generations, and Savings Plan utilization.

### Savings Plan vs RI

| Factor | RI | Savings Plan |
|---|---|---|
| Discount | Slightly higher (Standard 3-yr RI vs Compute SP 3-yr) | Slightly lower, but more flexibility |
| Scope | Specific instance family (Standard) or class (Convertible) | Any instance family (Compute) or specific family (Instance SP) |
| Region | Specific region (Standard) or any (Convertible) | Compute SP: any region; Instance SP: specific region |
| AZ | Zonal or Regional | Regional (across all AZs) |
| Exchange | Standard: no; Convertible: yes | Automatic flexibility (no exchange needed for Compute SP) |
| Recommended default | Long-term steady-state single-family | Mixed / multi-family fleets |

## Burstable (t-family) credit reference

### Earn rate per family (credits/hour)

| Instance size | t3 (Intel) | t3a (AMD) | t4g (Graviton) |
|---|---|---|---|
| nano | 3 | 3 | 3 |
| micro | 6 | 6 | 6 |
| small | 12 | 12 | 12 |
| medium | 24 | 24 | 24 |
| large | 36 | 36 | 36 |
| xlarge | 54 | 54 | 54 |
| 2xlarge | 81 | 81 | 81 |

Each credit = 1 vCPU at 100% utilization for 1 minute. Earn rate scales
linearly with vCPU count.

### Spend rate formula

```
Spend rate (credits/hour) = CPU utilization % / 100 * vCPUs * 60
```

### Tipping point (when t-family becomes uneconomic)

At sustained CPU utilization above ~20-25% (varies by family), the credit
balance depletes and the workload hits the 20% baseline performance cliff
(unless Unlimited mode is enabled, in which case additional charges accrue).

For sustained CPU > 40%, migrating to m-family is cheaper than Unlimited
mode's ongoing overage charges.

## Network performance reference

### "Up to N Gbps" interpretation

| Family | Documented network | Real-world sustained |
|---|---|---|
| m5.large, c5.large, r5.large | "Up to 10 Gbps" | ~5 Gbps sustained (bursts to 10) |
| m5.2xlarge, c5.2xlarge | "Up to 12 Gbps" | ~8 Gbps sustained |
| m5.4xlarge+ | "Up to 15 Gbps" | ~10 Gbps sustained |
| c6n.large | 25 Gbps guaranteed | 25 Gbps |
| c6n.9xlarge+ | 100 Gbps guaranteed | 100 Gbps |
| m7i.large | "Up to 12.5 Gbps" | ~8 Gbps sustained |
| m7i.16xlarge | 50 Gbps guaranteed | 50 Gbps |

"Up to" means burst — AWS does not guarantee sustained bandwidth at the
peak. Network-bound workloads should use n-family (guaranteed) or the
latest generation (better sustained).

### Enhanced Networking (ENA)

ENA is enabled by default on all current-gen instances (m5/c5/r5 and
later). HPC workloads should additionally enable EFA (Elastic Fabric
Adapter) on supported instances (c5n.9xlarge+, p4d, p5, hpc6a, hpc7g).

## Rightsizing decision rules of thumb

| Observation | Recommendation |
|---|---|
| CPU avg < 30% + Memory avg < 50% | Downsize 1 size |
| CPU avg < 10% + Memory avg < 30% | Downsize 2 sizes |
| CPU max > 70% sustained | Upsize 1 size (CPU-bound) |
| Memory max > 80% sustained | Upsize 1 size (memory-bound) or migrate to r-family |
| Network > 50% of limit sustained | Migrate to n-family or upsize |
| Disk ops > 70% of provisioned | Migrate to storage-optimized family or use io2 EBS |
| t-family CPUCreditBalance chronically < 50 | Enable Unlimited or migrate to m-family |
| Workload ARM-compatible + on x86 | Migrate to Graviton equivalent |
| On-Demand pricing on steady-state | Commit to RI or Savings Plan |
| Fleet > 5 instances of same type | Batch-rightsizing + Compute Savings Plan |

## Common false positives in rightsizing

| Observation | False positive: do NOT recommend downsize |
|---|---|
| CPU low, Memory high | Workload is memory-bound; needs MORE memory, not smaller instance |
| Low CPU during weekend only | Workload is weekday-heavy; pull business-hours data separately |
| Low average CPU but periodic spikes | Burstable pattern; check P95/P99, not average |
| Recently-deployed instance (< 14 days) | Workload still ramping; wait for steady-state |
| Instance in Auto Scaling Group | ASG manages sizing; right-size the launch template, not individual instances |
| Stopped instances in metrics | Filter out stopped time; metrics are skewed |
| Test/staging instances during off-hours | Idle by design; tag and exclude from production rightsizing |

## AWS Cost Explorer queries for baseline spend

```bash
# Identify top compute spend over last 30 days
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '-30 days' +%F),End=$(date +%F) \
  --granularity DAILY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE Type=DIMENSION,Key=INSTANCE_TYPE \
  --filter '{"Dimensions":{"Service":["Amazon Elastic Compute Cloud - Compute"]}}' \
  --output json

# Identify RI/Savings Plan coverage gap
aws ce get-savings-plans-coverage \
  --time-period Start=$(date -d '-30 days' +%F),End=$(date +%F) \
  --granularity MONTHLY --output json

# Identify idle EC2 instances (low NetworkIn + low CPU)
aws ec2 describe-instances --filters Name=instance-state-name,Values=running \
  --output json | jq '.Reservations[].Instances[] | select(.State.Name == "running") | .InstanceId'
# Then for each, pull CPU and NetworkIn over 14 days; flag if both < 5%
```
