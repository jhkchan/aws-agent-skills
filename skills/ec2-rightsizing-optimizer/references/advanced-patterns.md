# Advanced Patterns (load on demand) — EC2 Rightsizing Optimizer

Quick start rules, Mindset, Philosophy, the Step 0 expert-behaviour catalogue, Graviton and pricing-model deep-dives, the deterministic network-limit formula, and 2024-2026 feature notes, moved verbatim from SKILL.md.


---

## Quick start — headline rules (moved from SKILL.md)

- **Memory data is the load-bearing signal.** CPU utilization without
  memory data tells you nothing about memory-bound workloads (the #1
  cause of false-positive right-sizes). If `MemoryUtilization` is absent
  from CloudWatch metrics, the verdict is BLOCKED → install the
  CloudWatch Agent, wait 14-30 days, re-evaluate. Never recommend a
  downsize based on CPU-only data.
- **Decision matrix:**
  - CPU < 30% avg AND Memory < 50% avg → downsize 1-2 sizes.
  - CPU > 70% sustained OR Memory > 80% → upsize.
  - Burstable t-family: check CPUCreditBalance; chronic exhaustion →
    Unlimited mode or migrate to m-family.
  - Network-bound (NetworkIn or NetworkOut > 50% of instance limit) →
    Enhanced Networking or larger instance.
- **Graviton first.** For compatible workloads (JVM, Python, Go,
  containerized), the AWS Graviton family (m7g/c7g/r7g/i7g) offers up to
  40% better price-performance than equivalent x86. Check application
  compatibility before recommending.
- **Pricing model gates the savings.** Right-sizing an On-Demand instance
  captures the gross savings. Adding a 3-year Convertible RI captures
  30-72% on top. A right-size WITHOUT a pricing-model review leaves the
  largest savings on the table.

## Mindset (moved from SKILL.md)

EC2 right-sizing is a cost-quality decision, not a pure utilization
exercise. The goal is the smallest instance class/type that comfortably
handles peak workload without performance regression — not the absolute
minimum that satisfies the average. A right-size that triggers a customer-
visible latency spike costs more than it saves. The decision matrix below
favours conservatism: downsize in 1-2 size increments, verify with load
testing for production, and always provide a rollback path.

## Philosophy — four senior-FinOps behaviours (moved from SKILL.md)

Four behaviours separate a senior FinOps engineer from a generalist:

- **Memory data is non-negotiable for downsizing.** Without the
  CloudWatch Agent reporting `mem_used_percent`, you cannot tell whether
  an idle CPU instance is genuinely underutilized (downsize candidate)
  or memory-pressured (right-size would crash the workload). CPU is the
  visible signal; memory is the load-bearing constraint. A downsize
  recommendation without memory data is a guess, not an engineering
  decision.
- **Burstable t-family has a hidden cost cliff.** t3/t3a instances earn
  CPU credits at idle and spend them under load. Below the credit-balance
  floor, performance drops to a 20% baseline — a 5x latency spike. The
  symptom is intermittent slowdowns during business hours. Operators who
  right-size INTO a t-family without checking the workload's burst pattern
  discover the cliff at the worst possible moment.
- **Graviton compatibility must be verified, not assumed.** Most JVM,
  Python, Go, and containerized workloads run on Graviton unchanged. C++,
  Rust, and any code with platform-specific binaries (native libraries,
  ARM-incompatible .so files) require recompilation or replacement.
  Recommending Graviton without checking compatibility produces a
  migration that fails at runtime — sometimes subtly (wrong endianness in
  serialization) rather than loudly (binary won't load).
- **The pricing model is half the savings.** A typical On-Demand fleet
  spends 60-70% more than the same fleet on a 3-year Compute Savings Plan.
  Right-sizing captures utilization savings; pricing-model optimization
  captures commitment savings. Doing one without the other leaves money
  on the table. Always pair a rightsizing recommendation with a pricing-
  model recommendation.

## Step 0: Non-obvious behaviours that change the recommendation (moved from SKILL.md)

These are the operational gotchas a senior FinOps engineer knows from
incident experience — each one routes a recommendation away from the
obvious choice:

- **`MemoryUtilization` is the load-bearing constraint for downsizing.**
  CPU utilization is the visible signal; memory is the silent killer. An
  instance at 5% CPU and 90% memory is NOT a downsize candidate — it's
  a memory-bound workload that needs MORE memory, not less. The decision
  matrix checks BOTH dimensions; downsize requires both to be low.

- **Burstable t-family CPUCreditBalance depletion is a hidden performance
  cliff.** t3/t3a/t4g instances earn CPU credits at idle (proportional to
  instance size) and spend them under load. Below the floor, performance
  drops to a 20% baseline. The symptom is intermittent slowdowns during
  business hours that don't appear in the average utilization. Always
  check `CPUCreditBalance` over the observation window — if it chronically
  drops below ~50 credits, the workload is not burst-compatible. Migrate
  to a non-burstable (m-family) instance or enable Unlimited mode (which
  charges for overage credits but maintains performance).

- **Graviton (ARM) compatibility must be verified, not assumed.**
  - JVM (Java 11+): runs unchanged.
  - Python: pure-Python works; C-extension packages (numpy, pandas,
    psycopg2) need ARM wheels — most are available in 2024+.
  - Go: pure-Go works; CGO with x86 assembly needs recompile.
  - Node.js: works; native addons (.node files) need ARM builds.
  - C/C++ and Rust: must recompile for aarch64; some dependencies may
    not have ARM builds.
  - Docker images: multi-arch images work; single-arch x86 images must
    be rebuilt for arm64.
  - Always check `aws ec2 describe-instance-types --instance-types <type>
    --query 'InstanceTypes[].ProcessorInfo.SupportedArchitectures'`
    before recommending Graviton.

- **Network performance is instance-class-capped, not burstable (except
  on t-family).** A `m5.large` has "Up to 10 Gbps" (burst, not guaranteed);
  a `m5.2xlarge` has "Up to 10 Gbps"; a `c5n.18xlarge` has 25 Gbps
  guaranteed. Network-bound workloads (real-time streaming, HFT, large
  data transfers) should migrate to network-optimized families
  (c5n/c6n/m6n/r6n) or use Enhanced Networking (ENA) where available.
  The symptom of network saturation: `NetworkIn + NetworkOut` sustained
  > 50% of the instance's documented limit.

- **EBS-optimized instances are the default for current-generation
  instances.** m5/c5/r5 and later all have EBS optimization built in.
  Older generations (m3/c3/m4/c4 — m4.16xlarge is the exception) need
  `--ebs-optimized` flag or may lack the feature. EBS-bound workloads
  (heavy database I/O, large sequential reads) on legacy generations
  should migrate to current-gen for EBS performance alone.

- **Reserved Instances are zone-specific (until Convertible or Regional).**
  A Zonal RI for `m5.2xlarge` in `us-east-1a` does not apply to an
  `m5.2xlarge` in `us-east-1b`. Regional RIs (and all Savings Plans)
  apply across AZs in the region. When right-sizing across AZs, prefer
  Regional RIs or Compute Savings Plans to maintain flexibility.

- **Spot Instance interruptions make Spot unsuitable for stateful
  workloads.** Spot can be reclaimed with 2 minutes warning. Use Spot
  only for stateless, fault-tolerant, or batch workloads (CI runners,
  batch processing, containerized microservices with auto-scaling).
  NEVER recommend Spot for databases, queues, or singleton services.

- **Convertible RIs allow instance-family changes; Standard RIs do not.**
  A 3-year Standard RI for `m5.2xlarge` cannot be exchanged for a `c5.2xlarge`
  if the workload shape changes. Convertible RIs (slightly lower discount)
  allow exchanges within the same instance family and across families.
  For workloads with uncertain growth, Convertible RIs or Compute Savings
  Plans provide flexibility insurance.

- **Savings Plans apply to spend, not instances.** A Compute Savings Plan
  commits to $X/hour of compute spend (any instance family, any region,
  any OS). An Instance Savings Plan commits to a specific instance family
  in a specific region (more discount, less flexibility). Compute Savings
  Plans are the most flexible commitment vehicle and the recommended
  default for mixed fleets.

- **Cross-family migrations (e.g., m5 → t3) require validation.** Same-
  family right-sizes (m5.2xlarge → m5.large) are low-risk: identical
  architecture, identical drivers, only size changes. Cross-family
  migrations may need AMI changes (different virtualization: Nitro vs
  Xen), driver compatibility checks, and application testing. Always flag
  cross-family migrations as higher-effort remediation.

- **The 7th-generation (m7i/c7i/r7i) and Graviton (m7g/c7g/r7g) instances
  offer DDR5 memory and better networking.** Migrating from 5th-gen
  (m5/c5/r5) to 7th-gen often improves performance 15-25% at the same
  hourly price — a "free" rightsizing opportunity that doesn't show up
  in utilization metrics. Consider as part of any rightsizing batch.

- **Aurora Serverless v2, RDS Proxy, and ECS Fargate have different
  rightsizing models.** This skill is EC2-specific. For Aurora/RDS,
  refer to the database rightsizing docs. For ECS/Fargate, right-size
  the task definition CPU/memory, not the underlying EC2 host.

- **`describe-instance-types` is the source of truth for specs.** Don't
  rely on memorized instance specs — they change with new generations.
  Always query:
  ```bash
  aws ec2 describe-instance-types --instance-types m7i.2xlarge \
    --query 'InstanceTypes[].{VCpuInfo:VCpuInfo, MemoryInfo:MemoryInfo, NetworkInfo:NetworkInfo}' --output json
  ```

  **Parsing the response for a rightsizing decision:**

  ```bash
  aws ec2 describe-instance-types --instance-types <candidate-type> \
    --output json | jq '.InstanceTypes[] | {
      vcpus: .VCpuInfo.DefaultVCpus,
      memory_gib: (.MemoryInfo.SizeInMiB / 1024),
      architectures: .ProcessorInfo.SupportedArchitectures,
      network_perf: .NetworkInfo.NetworkPerformance,        # "Up to 12.5 Gbps"
      ebs_optimized: .EbsInfo.EbsOptimizedSupport,           # "supported" | "unsupported"
      ebs_throughput: .EbsInfo.EbsOptimizedInfo.BandwidthGbps,
      burstable: (.BurstablePerformance.Supported // false),  # true for t-family
      instance_storage: .InstanceStorageInfo.Disks[].SizeInGB,
      supported_virtualization: .SupportedVirtualizationTypes  # ["hvm"] required for current gen
    }'
  ```

  **Decision gates when comparing candidate vs current type:**

  | Field | Gate | Why it matters |
  |---|---|---|
  | `SupportedArchitectures` includes `arm64` | Graviton path available (otherwise stay x86). | Determines AMI family and runtime compatibility. |
  | `EbsInfo.EbsOptimizedSupport == "supported"` | Required for EBS-heavy workloads. | Legacy m4/c4 lack this by default; current-gen includes it. |
  | `BurstablePerformance.Supported == true` | Candidate is t-family — apply Step 6 credit math before recommending. | A downsize into t-family without credit math triggers the performance cliff. |
  | `NetworkInfo.NetworkPerformance` starts with "Up to" | Burst bandwidth; derate by 30% for sustained ceiling. | Network-bound workloads need guaranteed bandwidth (n-family). |
  | `MemoryInfo.SizeInMiB / VCpuInfo.DefaultVCpus` ratio | Match to workload shape (general ~1:4, compute 1:2, memory 1:8). | Wrong ratio = wrong family even if raw size seems correct. |
  | `InstanceStorageInfo` present | Candidate has NVMe/SSD local storage. | Required for storage-optimized (i4i, im4gn) workloads; costs more if unused. |

  If ANY of these fields is absent from the response, the candidate
  type is not available in the region or the API version is stale.
  Fall back to a documented alternative from
  `references/instance-selection-reference.md` rather than guessing.

## Step 7: Graviton (ARM) migration evaluation (moved from SKILL.md)

Evaluate Graviton compatibility for any current-gen x86 instance. The
Graviton family (m7g/c7g/r7g/i7g) offers up to 40% better price-
performance than equivalent x86.

**Compatibility check:**
- Operating system: Amazon Linux 2023, Ubuntu 22.04+, Debian 11+ all
  support arm64.
- Application runtime:
  - JVM (Java 11+): full support.
  - Python: pure-Python and most C-extension packages support arm64
    (numpy, pandas, psycopg2-binary in 2024+).
  - Go: full support, including cross-compile via `GOOS=linux GOARCH=arm64`.
  - Node.js: full support; native addons may need rebuild.
  - C/C++ and Rust: recompile required; check dependencies for arm64.
- Docker images: multi-arch images (manifest list with arm64 entry) work;
  x86-only images must be rebuilt via `docker buildx`.

**Savings estimate:**
- Graviton hourly price is typically 10-20% lower than the equivalent
  x86 (e.g., m7g.large vs m7i.large).
- Graviton performance per vCPU is often 15-25% better (depending on
  workload).
- Combined price-performance improvement: up to 40%.

**Migration risk:**
- LOW: pure-JVM, Python, Go, containerized workloads with multi-arch
  images.
- MEDIUM: workloads with native addons or C-extension dependencies
  (verify arm64 wheel availability).
- HIGH: C/C++ applications, workloads with platform-specific binaries
  (x86 assembly, endianness-sensitive serialization).

## Step 8: Pricing model optimization (moved from SKILL.md)

After utilization-based rightsizing, evaluate the pricing model. This is
where the largest savings typically live.

**Pricing model decision tree:**

| Workload pattern | Recommended model | Savings vs On-Demand |
|---|---|---|
| Steady-state 24/7, predictable (database, app server) | 3-year Convertible RI or 3-year Compute Savings Plan | 50-72% |
| Steady-state but uncertain growth | 1-year Compute Savings Plan (renewable) | 30-40% |
| Dev/test, business-hours only | 1-year Convertible RI or Scheduled RI | 30-50% |
| Batch, fault-tolerant, horizontally scalable | Spot Instances | Up to 90% |
| Mixed fleet (some steady, some variable) | Compute Savings Plan for the baseline + On-Demand/Spot for the variable portion | Varies |

**Commitment laddering (recommended approach):**
1. Identify the baseline (steady-state) compute spend. Commit to a
   1-year Compute Savings Plan for this amount (low risk, flexible).
2. After 30 days of additional observation, extend the commitment to a
   3-year Compute Savings Plan or Convertible RI (locks in deeper
   discount).
3. Use Spot for batch and fault-tolerant workloads (CI runners, batch
   jobs, autoscaled microservices).
4. Use On-Demand only for genuine spiky workloads and short-lived
   experiments.

## Network-limit calculation (concrete formula) (moved from SKILL.md)

D7 references "Network > 50% of limit" without defining the limit. Use
this formula to make the threshold deterministic:

```
instance_limit_Mbps =
  describe-instance-types.NetworkInfo.NetworkPerformance
    parsed from the documented "Up to N Gbps" or "N Gbps" string.

utilization_pct =
  ( max(NetworkIn_bytes_per_sec, NetworkOut_bytes_per_sec)
    / (instance_limit_Mbps * 125000) ) * 100

# NetworkIn/Out come from CloudWatch get-metric-statistics,
# statistic=Maximum, period=3600, over the 14-30 day window.
# Use the MAX, not the average — bursts saturate the interface
# even when the average is modest.
```

| `utilization_pct` (peak hour) | Verdict contribution |
|---|---|
| > 80% sustained > 1 hour/day | `OPPORTUNITY_FOUND` (upsize or migrate to n-family). Performance risk is active. |
| 50-80% sustained | `OPPORTUNITY_FOUND` if combined with another dimension; otherwise surface as MEDIUM-severity finding. |
| < 50% | Network is not the bottleneck; proceed with other dimensions. |

For "Up to N Gbps" instances, treat N as the burst ceiling, not the
sustained limit — subtract ~30% to derive the realistic sustained
ceiling (e.g., m5.large "Up to 10 Gbps" → ~7 Gbps sustained).
Guaranteed-bandwidth families (c6n, m6n, r6n, p5) use the documented
value directly.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Graviton 4 (2024-2025):** Broad rollout across i8g, r8g, and other
  families. Up to 30% better performance than Graviton 3. Auditors
  should re-evaluate Graviton migration opportunities even on workloads
  that were not Graviton-3-compatible.
- **7th-generation Intel and AMD instances (2024-2025):** m7i/c7i/r7i
  (Intel Sapphire Rapids) and m7a/c7a/r7a (AMD Genoa). DDR5 memory,
  better network performance, and 15-25% perf improvement over 6th-gen
  at the same price. Re-evaluate 5th-gen fleets for "free" upgrades.
- **Compute Savings Plans enhancements (2024):** More flexible commitment
  terms (8-hour, 24-hour, 36-hour). Easier to ladder commitments. Use
  for any fleet with uncertain growth.
- **Spot Placement Score (2024-2025):** Predicts Spot capacity
  availability before launch. Auditors should check SPS for Spot
  recommendations to avoid recommending Spot for capacity-constrained
  instance types.
- **Instance Type Calculator (2024-2025):** AWS-hosted tool for
  comparing instance types across regions with pricing. Auditors should
  reference for accurate pricing in savings estimates.
- **EBS optimization defaults (2024):** All current-gen instances
  (m5/c5/r5 and later) include EBS-optimized at no extra charge. Legacy
  instances (m4.16xlarge, c4.10xlarge) still charge. Auditors should
  flag legacy instances for migration.
