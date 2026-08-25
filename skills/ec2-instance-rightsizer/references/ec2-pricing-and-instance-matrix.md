# EC2 Pricing and Instance Matrix Reference

Supplementary reference for the EC2 Instance Rightsizer skill. Loaded
on-demand when detailed pricing math, instance family comparisons,
Graviton compatibility matrices, or CWAgent metric references are needed.

## EC2 on-demand pricing (us-east-1, Linux, 2026, USD/hour)

### General purpose (x86_64)

| Instance | vCPU | RAM (GB) | Network | $/hour | Generation |
|---|---|---|---|---|---|
| m5.large | 2 | 8 | Up to 10 Gbps | $0.096 | 5th |
| m5.xlarge | 4 | 16 | Up to 10 Gbps | $0.192 | 5th |
| m5.2xlarge | 8 | 32 | Up to 10 Gbps | $0.384 | 5th |
| m5.4xlarge | 16 | 64 | Up to 10 Gbps | $0.768 | 5th |
| m6i.large | 2 | 8 | Up to 12.5 Gbps | $0.096 | 6th (Ice Lake) |
| m6i.xlarge | 4 | 16 | Up to 12.5 Gbps | $0.192 | 6th |
| m6i.2xlarge | 8 | 32 | Up to 12.5 Gbps | $0.384 | 6th |
| m6i.4xlarge | 16 | 64 | Up to 12.5 Gbps | $0.768 | 6th |
| m7i.large | 2 | 8 | Up to 12.5 Gbps | $0.090 | 7th (Sapphire Rapids) |
| m7i.xlarge | 4 | 16 | Up to 12.5 Gbps | $0.180 | 7th |
| m7i.2xlarge | 8 | 32 | Up to 12.5 Gbps | $0.360 | 7th |

### General purpose (Graviton arm64)

| Instance | vCPU | RAM (GB) | Network | $/hour | Graviton gen |
|---|---|---|---|---|---|
| m6g.large | 2 | 8 | Up to 10 Gbps | $0.077 | Graviton2 |
| m6g.xlarge | 4 | 16 | Up to 10 Gbps | $0.154 | Graviton2 |
| m6g.2xlarge | 8 | 32 | Up to 10 Gbps | $0.308 | Graviton2 |
| m7g.large | 2 | 8 | Up to 15 Gbps | $0.080 | Graviton3 |
| m7g.xlarge | 4 | 16 | Up to 15 Gbps | $0.160 | Graviton3 |
| m7g.2xlarge | 8 | 32 | Up to 15 Gbps | $0.320 | Graviton3 |

### Compute optimized (x86_64 and Graviton)

| Instance | vCPU | RAM (GB) | $/hour | Architecture |
|---|---|---|---|---|
| c5.large | 2 | 4 | $0.085 | x86_64 |
| c5.2xlarge | 8 | 16 | $0.340 | x86_64 |
| c6i.large | 2 | 4 | $0.085 | x86_64 |
| c6i.2xlarge | 8 | 16 | $0.340 | x86_64 |
| c7i.large | 2 | 4 | $0.080 | x86_64 |
| c6g.large | 2 | 4 | $0.068 | arm64 |
| c6g.2xlarge | 8 | 16 | $0.272 | arm64 |
| c7g.large | 2 | 4 | $0.071 | arm64 |
| c7g.2xlarge | 8 | 16 | $0.284 | arm64 |

### Memory optimized

| Instance | vCPU | RAM (GB) | $/hour | Architecture |
|---|---|---|---|---|
| r5.large | 2 | 16 | $0.126 | x86_64 |
| r5.2xlarge | 8 | 64 | $0.504 | x86_64 |
| r6i.large | 2 | 16 | $0.126 | x86_64 |
| r6g.large | 2 | 16 | $0.100 | arm64 |
| r6g.2xlarge | 8 | 64 | $0.403 | arm64 |
| r7g.large | 2 | 16 | $0.105 | arm64 |
| r7g.2xlarge | 8 | 64 | $0.420 | arm64 |

### Burstable (t-family)

| Instance | vCPU | RAM (GB) | Baseline | Credits/hr | $/hour | Arch |
|---|---|---|---|---|---|---|
| t3.nano | 2 | 0.5 | 5% | 6 | $0.0052 | x86_64 |
| t3.micro | 2 | 1 | 10% | 12 | $0.0104 | x86_64 |
| t3.small | 2 | 2 | 20% | 24 | $0.0208 | x86_64 |
| t3.medium | 2 | 4 | 20% | 24 | $0.0416 | x86_64 |
| t3.large | 2 | 8 | 30% | 36 | $0.0832 | x86_64 |
| t3.xlarge | 4 | 16 | 40% | 96 | $0.1664 | x86_64 |
| t3.2xlarge | 8 | 32 | 40% | 192 | $0.3328 | x86_64 |
| t4g.nano | 2 | 0.5 | 6% | 7.2 | $0.0034 | arm64 |
| t4g.micro | 2 | 1 | 10% | 12 | $0.0067 | arm64 |
| t4g.small | 2 | 2 | 20% | 24 | $0.0134 | arm64 |
| t4g.medium | 2 | 4 | 20% | 24 | $0.0269 | arm64 |
| t4g.large | 2 | 8 | 30% | 36 | $0.0538 | arm64 |
| t4g.xlarge | 4 | 16 | 40% | 96 | $0.1076 | arm64 |
| t4g.2xlarge | 8 | 32 | 40% | 192 | $0.2150 | arm64 |

t4g is Graviton2-based and ~35% cheaper than equivalent t3 instances.

### Unlimited mode surcharge

| Resource | Surcharge |
|---|---|
| Borrowed vCPU-hour (beyond earned credits) | $0.05 |
| This applies when CPUCreditBalance goes negative under Unlimited mode | Charged per-second, minimum 60 seconds |

## Generation migration paths

### Same-architecture upgrades (LOW risk)

| From | To | Price-performance gain | Migration method |
|---|---|---|---|
| m4 | m6i / m7i | ~20-30% | `modify-instance-attribute` (stop/start) |
| c4 | c6i / c7i | ~25-35% | `modify-instance-attribute` |
| r4 | r6i / r7i | ~20-30% | `modify-instance-attribute` |
| t2 | t3 | ~15-20% | `modify-instance-attribute` |
| m5 | m6i | ~10-15% | `modify-instance-attribute` |
| m5 | m7i | ~15-25% | `modify-instance-attribute` |
| c5 | c6i / c7i | ~10-15% | `modify-instance-attribute` |
| r5 | r6i / r7i | ~10-15% | `modify-instance-attribute` |

Same-architecture upgrades are done via stop → `modify-instance-attribute`
→ start. No AMI change needed (same ISA).

### Cross-architecture: Graviton migration (MEDIUM risk)

| From | To | Cost saving | Migration method |
|---|---|---|---|
| m6i | m6g | ~20% | NEW instance from arm64 AMI |
| m6i | m7g | ~17% + better perf | NEW instance from arm64 AMI |
| c6i | c6g | ~20% | NEW instance from arm64 AMI |
| c6i | c7g | ~17% + better perf | NEW instance from arm64 AMI |
| r6i | r6g | ~20% | NEW instance from arm64 AMI |
| r6i | r7g | ~17% + better perf | NEW instance from arm64 AMI |
| t3 | t4g | ~35% | NEW instance from arm64 AMI |

Graviton migrations ALWAYS require a new instance launch from an arm64
AMI. You cannot change the architecture of a running instance.

## Graviton compatibility matrix by runtime

| Runtime / stack | ARM64 support | Migration risk | Key check |
|---|---|---|---|
| Java (Corretto, OpenJDK) | Full | LOW | Verify no JNI with x86 native libs |
| Python (CPython 3.8+) | Full | LOW | Verify C-extension deps have aarch64 wheels |
| Node.js (16+) | Full | LOW | Verify native addons (node-gyp) |
| Go | Full | LOW | Recompile with `GOARCH=arm64 GOOS=linux` |
| Rust | Full | LOW | `rustc --target aarch64-unknown-linux-gnu` |
| .NET 6+ | Full | MEDIUM | Verify native deps; test thoroughly |
| Ruby | Full | LOW | Verify native gem extensions |
| C/C++ | Requires recompile | HIGH | Watch for x86 intrinsics, inline asm, endianness |
| Assembly | Requires rewrite | VERY HIGH | Full rewrite for ARM ISA |
| Docker (multi-arch) | Full | MEDIUM | Build `--platform linux/arm64`; test image |
| Docker (single-arch amd64) | Requires rebuild | MEDIUM | Rebuild from arm64 base image |

### Checking Python wheel availability for arm64

```bash
# Check if a package has aarch64 wheels on PyPI
pip install --platform aarch64 --only-binary=:all: <package-name>

# If this succeeds, the wheel is available.
# If it fails, the package needs compilation or is x86-only.
```

### Checking Docker image architecture

```bash
# Inspect a Docker image manifest for architecture support
docker manifest inspect <image>:<tag> | jq '.manifests[].platform.architecture'
# Look for "arm64" in the output
```

## CWAgent metric reference

The CloudWatch Agent is the ONLY source for guest OS memory metrics.
Without it, the hypervisor-level `AWS/EC2` namespace has CPU, network,
and disk — but NO memory.

### Installing CWAgent for memory metrics

```bash
# Install via SSM (recommended)
aws ssm send-command \
  --document-name "AWS-ConfigureAWSPackage" \
  --instance-ids i-0abc123def456 \
  --parameters '{"action":["Install"],"name":["AmazonCloudWatchAgent"]}'

# Configure to collect memory
# CWAgent config JSON (push via SSM Parameter Store):
{
  "metrics": {
    "metrics_collected": {
      "mem": {
        "measurement": ["used_percent"],
        "metrics_collection_interval": 60,
        "resources": ["*"]
      }
    }
  }
}
```

### CWAgent metrics for right-sizing

| Metric | Namespace | Dimension | Unit | Use |
|---|---|---|---|---|
| `mem_used_percent` | CWAgent | InstanceId | Percent | Memory utilization (PRIMARY for downsize) |
| `mem_used` | CWAgent | InstanceId | Megabytes | Absolute memory used |
| `mem_total` | CWAgent | InstanceId | Megabytes | Total memory (sanity check vs instance spec) |
| `swap_used_percent` | CWAgent | InstanceId | Percent | Swap usage (if > 0, memory is tight) |
| `disk_used_percent` | CWAgent | InstanceId, path | Percent | Disk utilization (instance store) |
| `cpu_usage_active` | CWAgent | InstanceId | Percent | Guest-level CPU (cross-check with hypervisor) |

### CWAgent vs AWS/EC2 namespace

| Metric | AWS/EC2 (hypervisor) | CWAgent (guest OS) |
|---|---|---|
| CPUUtilization | YES (`CPUUtilization`) | YES (`cpu_usage_active`) |
| Memory | NO | YES (`mem_used_percent`) |
| Network | YES (`NetworkIn`, `NetworkOut`) | YES (`net_bytes_in`, etc.) |
| Disk I/O | YES (`DiskReadOps`, `DiskWriteOps`) | YES (`diskio_reads`, etc.) |

**If `mem_used_percent` is absent, CWAgent is not installed.** For
downsize candidates, emit NEED_MORE_INFO (MEDIUM confidence fallback
if Compute Optimizer agrees and the workload is not memory-sensitive).

## Compute Optimizer EC2 finding reference

### Finding types

| Finding | Meaning | Right-sizing action |
|---|---|---|
| `Optimized` | Instance is right-sized | No action |
| `Underprovisioned` | Instance is too small | Upsize (CPU or memory pressure) |
| `Overprovisioned` | Instance is too large | Downsize 1-2 sizes |

### Finding reason codes

| Reason code | Interpretation |
|---|---|
| `CPUUnderprovisioned` | CPU > 90% sustained — upsize |
| `CPUOverprovisioned` | CPU < 30% sustained — downsize candidate |
| `MemoryUnderprovisioned` | Memory pressure (requires CWAgent) — upsize |
| `MemoryOverprovisioned` | Memory < 50% (requires CWAgent) — downsize candidate |
| `NetworkBandwidthOverprovisioned` | Low network utilization — downsize or switch to smaller-network instance |
| `DiskIOPSOverprovisioned` | Low disk I/O — consider EBS-optimized smaller instance |

### Compute Optimizer recommendation options

```bash
aws compute-optimizer get-ec2-instance-recommendations \
  --instance-arns arn:aws:ec2:us-east-1:<acct>:instance/i-0abc123def456 \
  --query 'instanceRecommendations[0].recommendationOptions'
```

Each option includes:
- `instanceType`: recommended type
- `performanceRisk`: 0-4 scale (0 = low risk, 4 = high risk — workload
  may not perform well)
- `projectedUtilizationMetrics`: CPU, memory, network at the recommended
  type
- `rank`: 1 (best), 2, 3

**Performance risk > 2 warrants a test before cutover.**

## Workload-specific sizing rules (detailed)

### Web server (Nginx, Apache, HAProxy)

- **Key metric:** CPU p95, active connections
- **Downsize tolerance:** HIGH — web servers are stateless
- **Minimum viable:** 2 vCPU for HA (1 vCPU causes connection queuing)
- **Memory:** 4 GB sufficient for most web servers (cache is at CDN/Redis layer)
- **Recommended family:** c-family (compute-optimized) for high-request,
  m-family for general use

### Application server (Tomcat, JVM, Django, Rails)

- **Key metric:** Memory utilization, GC pause times
- **Downsize tolerance:** MEDIUM — JVM heap needs headroom
- **Minimum viable:** Enough RAM for heap + 30% overhead for metaspace,
  thread stacks, direct buffers
- **Rule of thumb:** JVM heap should be 50-70% of instance RAM
- **Recommended family:** m-family (balanced), r-family for large heaps

### Database (PostgreSQL, MySQL, Oracle)

- **Key metric:** Memory utilization, disk I/O, buffer cache hit ratio
- **Downsize tolerance:** LOW — memory is buffer cache
- **Minimum viable:** Memory must hold the working set
  (PostgreSQL: `shared_buffers` = 25% of RAM; MySQL: `innodb_buffer_pool_size`
  = 50-70% of RAM)
- **NEVER downsize based on CPU alone.** Low CPU + high memory = cache
  is working as designed.
- **Recommended family:** r-family (memory-optimized)

### Batch processing (ETL, video encoding, ML training)

- **Key metric:** CPU avg, job completion time, Spot interruption rate
- **Downsize tolerance:** HIGH — can use Spot, tolerate latency
- **Minimum viable:** Size to job deadline (job_time = data_volume /
  throughput)
- **Recommended family:** c-family (compute-optimized) for CPU-bound,
  r-family for memory-bound ML

### Cache (Redis, Memcached, Elasticsearch)

- **Key metric:** Memory utilization, eviction count, cache hit ratio
- **Downsize tolerance:** VERY LOW — memory IS the data
- **Minimum viable:** Memory must hold the FULL dataset + 20% headroom
- **NEVER downsize if eviction count > 0.** Evictions mean data is being
  evicted — downsize will make it worse.
- **Recommended family:** r-family (memory-optimized)

### Dev / test

- **Key metric:** Cost (utilization is low by definition)
- **Downsize tolerance:** VERY HIGH — can stop when not in use
- **Minimum viable:** t3.nano / t4g.nano for basic dev
- **Action:** Stop non-production instances outside business hours.
  Schedule with Instance Manager or EventBridge.

## Regional pricing multipliers

Approximate multiplier vs us-east-1 for EC2 on-demand rates.

| Region | Multiplier | Notes |
|---|---|---|
| us-east-1, us-east-2, us-west-2 | 1.00x | Baseline |
| us-west-1 | 1.05-1.10x | Slight premium |
| eu-west-1, eu-west-2, eu-central-1 | 1.10-1.15x | EU premium |
| ap-southeast-1, ap-southeast-2 | 1.12-1.18x | APAC premium |
| ap-northeast-1 (Tokyo) | 1.10-1.15x | |
| ap-south-1 (Mumbai) | 1.15-1.25x | |
| sa-east-1 (São Paulo) | 1.35-1.50x | Highest premium |
| af-south-1 (Cape Town) | 1.30-1.45x | |

Always re-check via the AWS Pricing API for production estimates.

## Cost calculation worked examples

### Example 1: Downsize within family

```
Instance: i-0web01
Current type: m5.2xlarge ($0.384/h, 8 vCPU, 32 GB)
Proposed type: m5.large ($0.096/h, 2 vCPU, 8 GB)
Region: us-east-1, On-Demand
CPU avg: 3.2%, Memory avg: 28% (CWAgent)

Current monthly: $0.384 × 730 = $280.32
Projected monthly: $0.096 × 730 = $70.08
Monthly saving: $210.24 (75%)
Annual saving: $2,522.88
```

### Example 2: Downsize + generation upgrade

```
Instance: i-0app02
Current type: m5.xlarge ($0.192/h, 4 vCPU, 16 GB)
Proposed type: m6i.large ($0.096/h, 2 vCPU, 8 GB)
Region: us-east-1, On-Demand
CPU avg: 12%, Memory avg: 35% (CWAgent)

Current monthly: $0.192 × 730 = $140.16
Projected monthly: $0.096 × 730 = $70.08
Monthly saving: $70.08 (50%)
Annual saving: $840.96
```

### Example 3: Graviton migration

```
Instance: i-0api03
Current type: c6i.2xlarge ($0.340/h, 8 vCPU, 16 GB, x86_64)
Proposed type: c7g.2xlarge ($0.284/h, 8 vCPU, 16 GB, arm64)
Region: us-east-1, On-Demand
CPU avg: 45%, Memory avg: 55% (CWAgent)

Current monthly: $0.340 × 730 = $248.20
Projected monthly: $0.284 × 730 = $207.32
Monthly saving: $40.88 (16%)
Annual saving: $490.56
Note: Graviton migration also typically delivers ~20% better per-core
performance, so effective savings are higher (more throughput per $).
```

### Example 4: Savings Plan impact on right-sizing

```
Instance: i-0db04
Current type: r5.2xlarge ($0.504/h OD, 8 vCPU, 64 GB)
Proposed type: r6i.xlarge ($0.252/h OD, 4 vCPU, 32 GB)
Active Compute Savings Plan: 40% off (1-year, $10k/h commitment)
Region: us-east-1

OD monthly current: $0.504 × 730 = $367.92
SP effective current: $367.92 × 0.60 = $220.75
OD monthly projected: $0.252 × 730 = $183.96
SP effective projected: $183.96 × 0.60 = $110.38

Monthly saving (effective): $220.75 - $110.38 = $110.37
  (NOT $183.96 — the SP discount applies to both)
Annual saving (effective): $1,324.44
```

### Example 5: t3 Unlimited surcharge

```
Instance: i-0build05
Current type: t3.large ($0.0832/h, 2 vCPU, 8 GB)
CPUCreditBalance: trending negative (Unlimited enabled)
Borrowed credits: 200 vCPU-hours/month

Unlimited surcharge: 200 × $0.05 = $10.00/month
Total monthly: $0.0832 × 730 + $10.00 = $60.74 + $10.00 = $70.74

Alternative: migrate to m6i.large ($0.096/h, consistent CPU)
m6i monthly: $0.096 × 730 = $70.08

Conclusion: m6i is cheaper than t3+Unlimited when borrowing > ~150 hours.
```

### Example 6: Idle instance stop

```
Instance: i-0legacy06
Current type: m5.large ($0.096/h, 2 vCPU, 8 GB)
CPU avg: 0.3%, NetworkIn: <1 MB/h, DiskReadOps: <5/s
14-day observation: all idle criteria met
Termination protection: false (EBS-backed)

Current monthly: $0.096 × 730 = $70.08
Projected monthly: $0.00 (stopped)
Monthly saving: $70.08 (100%)
Annual saving: $840.96

Action: aws ec2 stop-instances --instance-ids i-0legacy06
Note: EBS volume continues to charge (~$0.10/GB-month for gp2).
      Total EBS cost remains until the instance is terminated.
```

## Graviton instance families (moved from SKILL.md)

**Graviton instance families:**
| Family | Graviton version | Equivalent x86 | Workload |
|---|---|---|---|
| t4g | Graviton2 | t3 | Burstable, low-cost |
| m6g / m7g | Graviton2 / Graviton3 | m6i / m7i | General purpose |
| c6g / c7g | Graviton2 / Graviton3 | c6i / c7i | Compute-optimized |
| r6g / r7g | Graviton2 / Graviton3 | r6i / r7i | Memory-optimized |
| x2gd | Graviton2 | x2iezn | Extreme memory |
