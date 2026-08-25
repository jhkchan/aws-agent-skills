---
name: ec2-rightsizing-optimizer
description: Right-sizes EC2 instances for cost optimization using a structured utilization-driven decision framework — gathers 14-30 day CloudWatch utilization data (CPUUtilization, NetworkIn/Out, DiskReadOps/WriteOps, and the load-bearing MemoryUtilization that requires the CloudWatch Agent), interprets Compute Optimizer findings (Optimized, Underprovisioned, Overprovisioned, Not-enough-data) with confidence gating, applies a rightsizing decision matrix (CPU < 30% + Memory < 50% → downsize; CPU > 70% sustained OR Memory > 80% → upsize; network-bound → Enhanced Networking or larger instance; burstable t-family → CPU credit balance check), selects instance families by workload shape (general-purpose m7i/m6i, compute c7i/c7a, memory r7i/r7a/x2idn, storage i4i/im4gn, GPU g5/p5), evaluates Graviton (ARM) migration opportunities with up to 40% better price-performance, and recommends pricing-model optimizations (On-Demand → Reserved Instance 1/3yr for steady-state with 30-72% savings, Compute/Instance Savings Plans for...
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation-document classification works from pasted Compute Optimizer findings and CloudWatch metrics. Live-account optimization uses aws ec2 describe-instances, aws cloudwatch get-metric-statistics, aws compute-optimizer get-ec2-instance-recommendations, aws ce get-cost-and-usage, and aws ec2 describe-instance-types (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: optimize
  skill_class: capability
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Right-sizing EC2 instances for cost optimization, planning a FinOps rightsizing batch, interpreting Compute Optimizer EC2 findings, evaluating Graviton (ARM) migration opportunities, selecting an instance family for a new workload, comparing pricing models (On-Demand / RI / Savings Plans / Spot), or building a monthly savings estimate for an optimization initiative.
  when_not_to_use: Auditing Compute Optimizer finding confidence on a single resource (use compute-optimizer-findings-auditor), EBS volume right-sizing (use compute-optimizer-findings-auditor for EBS findings), Lambda memory tuning (use compute-optimizer-findings-auditor), Fargate task sizing (use compute-optimizer-findings-auditor for ECS), or performance troubleshooting for a slow instance (use rds-connectivity-troubleshooter for database reachability, or Performance Insights / CloudWatch metrics directly for EC2). This skill focuses on cost-driven EC2 rightsizing decisions, not single-finding confidence audits or non-EC2 resources.
  activation_triggers: right-size EC2 instances, EC2 cost optimization, Compute Optimizer EC2 recommendations, EC2 underutilized, EC2 overprovisioned, FinOps EC2 savings, Graviton migration opportunity, EC2 Reserved Instance, Savings Plan recommendation, EC2 instance family selection, EC2 monthly savings estimate, EC2 fleet rightsizing, t-family CPU credit exhaustion, m5 to m7i migration, EC2 pricing model optimization, spot instance opportunity
  invocation_schema: 'Input: either (a) an EC2 instance identifier + live-account context, (b) a Compute Optimizer EC2 finding document, OR (c) CloudWatch utilization metrics (CPU, Memory, Network, Disk) for one or more instances with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/ MIGRATION_STEPS block per instance, where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL} and RECOMMENDATION includes the target instance type, family, pricing model, and Graviton flag.'
  invocation_example: "# Minimal valid input (offline finding classification):\nInstanceId: i-0abc123\nCurrent instance type: m5.2xlarge\nRegion: us-east-1\nCompute Optimizer finding: Overprovisioned\nFinding reasons: [\"CPUOverprovisioned\", \"MemoryOverprovisioned\"]\nUtilization metrics (last 30 days):\n  - CPUUtilization: avg=8%, max=15%, source=CloudWatch\n  - MemoryUtilization: avg=22%, max=30%, source=CloudWatchAgent\n  - NetworkIn: avg=0.05 MB/s, max=0.1 MB/s\n  - DiskReadOps+DiskWriteOps: avg=10/s, max=20/s\nRecommendation options:\n  - rank: 1, instanceType: t3.large, performanceRisk: 1,\n    savingsOpportunity: {savingsPercentage: 75, estimatedMonthlySavings: 150}\nPricing: On-Demand, no RI/Savings Plan commitment.\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EC2, right-sizing, cost optimization, Compute Optimizer, CloudWatch Agent, MemoryUtilization, CPUUtilization, NetworkIn, Graviton, ARM, m7i, c7i, r7i, i4i, g5, p5, Reserved Instance, Savings Plans, Spot Instances, FinOps, instance family selection, EBS-optimized, Enhanced Networking, burstable, t-family, CPU credit balance, price-performance
  tags: ec2, compute, cost-optimization, finops, right-sizing, graviton, compute-optimizer
---

# EC2 Rightsizing Optimizer

## Quick start

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

## Mindset

EC2 right-sizing is a cost-quality decision, not a pure utilization
exercise. The goal is the smallest instance class/type that comfortably
handles peak workload without performance regression — not the absolute
minimum that satisfies the average. A right-size that triggers a customer-
visible latency spike costs more than it saves. The decision matrix below
favours conservatism: downsize in 1-2 size increments, verify with load
testing for production, and always provide a rollback path.

## Philosophy

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

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| CPU < 30% avg AND Memory < 50% avg AND Network < 30% limit AND Disk low | **OPPORTUNITY_FOUND** (downsize) | Step 4 — downsize 1-2 sizes, prefer Graviton equivalent |
| CPU > 70% sustained OR Memory > 80% OR Network > 50% limit | **OPPORTUNITY_FOUND** (upsize — performance risk) | Step 5 — upsize to next class that resolves the bottleneck |
| Burstable t-family with CPUCreditBalance chronically near 0 | **OPPORTUNITY_FOUND** (architecture change) | Step 6 — migrate to m-family or enable Unlimited |
| Graviton-compatible workload on x86 with stable utilization | **OPPORTUNITY_FOUND** (price-performance) | Step 7 — Graviton migration during next AMI refresh |
| On-Demand pricing on steady-state workload | **OPPORTUNITY_FOUND** (pricing model) | Step 8 — RI or Compute Savings Plan |
| MemoryUtilization metric absent | **NEED_MORE_INFO** (BLOCKED — not ALREADY_OPTIMAL) | Install CloudWatch Agent, wait 14-30 days, re-evaluate |
| Compute Optimizer finding `Optimized` + metrics present + already on RI/SP | **ALREADY_OPTIMAL** | None — continue monitoring |
| Compute Optimizer finding `NotOptimized` (insufficient data) | **NEED_MORE_INFO** | Wait for additional observation |
| All thresholds pass for current type AND pricing already optimized | **OPTIMIZED** | None required |

See the ordered steps for edge cases (cross-family migration, EBS-bound
workloads, Spot-eligible workloads, multi-AZ fleets).

## Pre-flight: data gate (run before any right-sizing decision)

Right-sizing decisions are only as good as the underlying data. Several
data-quality conditions short-circuit the optimization — misclassifying
them produces recommendations that fail at runtime.

### Required data sources

```bash
# 1. Confirm CloudWatch Agent is reporting MemoryUtilization
aws ec2 describe-instances --instance-ids <id> --output json | \
  jq '.Reservations[].Instances[] | .InstanceId'

aws cloudwatch list-metrics --namespace CWAgent \
  --metric-name mem_used_percent \
  --dimensions Name=InstanceId,Value=<id> --output json

# 2. Pull 14-30 day utilization history
START=$(date -d '-30 days' +%FT%TZ)
END=$(date +%FT%TZ)

aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=<id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum,Minimum \
  --output json > cpu.json

aws cloudwatch get-metric-statistics --namespace CWAgent \
  --metric-name mem_used_percent \
  --dimensions Name=InstanceId,Value=<id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum,Minimum \
  --output json > mem.json

# 3. Confirm Compute Optimizer enrollment
aws compute-optimizer get-enrollment-status --output json
```

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `MemoryUtilization` metric absent (CWAgent not installed) | **NEED_MORE_INFO**: Install CWAgent, wait 14-30 days, re-evaluate. Do NOT recommend a downsize. |
| Observation window < 14 days | **NEED_MORE_INFO**: workload may reflect atypical load (deploy week, incident response, seasonal dip). Minimum 14 days; 30 days preferred. |
| Instance stopped for > 50% of window | Metrics are skewed. Re-pull after a stable 14-day running window. |
| Compute Optimizer enrollment `Inactive` | No Compute Optimizer findings to cross-reference. Rely on CloudWatch metrics directly. |
| Compute Optimizer `lastRefreshTimestamp` > 30 days old | Stale finding — workload may have changed. Re-run `get-ec2-instance-recommendations`. |
| Instance in `Stopped` state at evaluation time | Right-sizing is moot until the instance restarts. Note and skip. |

### Conflicting-data arbitration

When CloudWatch metrics and Compute Optimizer findings disagree (e.g.,
CloudWatch shows CPU 60% but Compute Optimizer says Overprovisioned),
trust CloudWatch. Compute Optimizer averages over 30 days and may smooth
out recent workload spikes. The freshest signal wins.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

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

### Step 1: Validate input and data sufficiency

If `MemoryUtilization` is absent from the input metrics (CWAgent not
installed), emit NEED_MORE_INFO with a specific installation instruction:

```text
TARGET: <instance-id>
VERDICT: NEED_MORE_INFO
REASON: MemoryUtilization metric is absent — CloudWatch Agent is not
  reporting mem_used_percent for this instance. Without memory data,
  a downsize recommendation is a guess, not an engineering decision.
RECOMMENDATION:
  1. Install the CloudWatch Agent on the instance with mem_used_percent
     enabled (see AWS docs: CWAgent installation guide).
  2. Wait 14-30 days for representative observation.
  3. Re-evaluate with CPU + Memory + Network + Disk data.
ESTIMATED_SAVINGS: $0 (cannot quantify without memory data)
MIGRATION_STEPS:
  - Install CWAgent (Linux): sudo yum install amazon-cloudwatch-agent
  - Configure mem_used_percent in the CWAgent config JSON
  - Validate: aws cloudwatch list-metrics --namespace CWAgent
    --metric-name mem_used_percent --dimensions Name=InstanceId,Value=<id>
```

If the observation window is < 14 days, emit NEED_MORE_INFO: "Observation
window is N days; minimum 14 days required for representative data."
Proceed only if both conditions are met.

### Step 2: Compute Optimizer reconciliation

If a Compute Optimizer finding is provided, reconcile with CloudWatch
metrics. Compute Optimizer's 30-day analysis is a sanity check; the
fresh CloudWatch signal wins on disagreement.

**Concrete parsing of `get-ec2-instance-recommendations` output:**

```bash
aws compute-optimizer get-ec2-instance-recommendations \
  --instance-arns arn:aws:ec2:us-east-1:<acct>:instance/<id> \
  --output json | jq '
    .instanceRecommendations[] | {
      instance_arn: .instanceArn,
      current_type: .currentInstanceType,
      finding: .finding,                  # Optimized | Underprovisioned | Overprovisioned
      finding_reasons: .findingReasonCodes,
      recommendations: [
        .recommendationOptions[] | {
          rank: .rank,                    # 1 = highest savings (may carry highest risk)
          type: .instanceType,
          performance_risk: .performanceRisk,  # 1 (safe) .. 5 (risky)
          vcpus: .instanceDigest.vCpu.vCpus,
          memory_gb: (.instanceDigest.instanceMemory.sizeInMiB / 1024),
          savings_pct: .savingsOpportunity.savingsPercentage,
          monthly_savings: .savingsOpportunity.estimatedMonthlySavings.amount
        }
      ],
      last_refresh: .lastRefreshTimestamp,
      utilization_metrics: .utilizationMetrics
    }'
```

| Field to verify | What it tells you | Action if missing/stale |
|---|---|---|
| `finding` | High-level classification (Optimized/Under/Over) | If absent, finding is `NotOptimized` due to insufficient data → emit NEED_MORE_INFO. |
| `recommendationOptions[].performanceRisk` | Risk that the recommended type cannot handle the workload (1=low ... 5=high) | Always prefer options with `performanceRisk ≤ 2` for production. If only risk ≥ 4 options exist, emit NEED_MORE_INFO and investigate manually. |
| `lastRefreshTimestamp` | When Compute Optimizer last re-analyzed | If > 30 days old, treat as stale; re-run `get-ec2-instance-recommendations` or rely on CloudWatch. |
| `utilizationMetrics[]` | Source data Compute Optimizer used | Cross-check against your CloudWatch pull. If they disagree, freshest CloudWatch wins. |
| `savingsOpportunity.estimatedMonthlySavings` | Dollar savings estimate | Sanity-check against your own hourly math (Step 9). Compute Optimizer uses list price; your actual RI/SP rate may differ. |

| Compute Optimizer finding | CloudWatch agreement | Action |
|---|---|---|
| `Overprovisioned` + HIGH confidence (Memory metric present, performanceRisk ≤ 2) | CPU < 30% AND Memory < 50% | Proceed to Step 4 (downsize). |
| `Overprovisioned` + LOW confidence (Memory inferred, performanceRisk ≥ 4) | — | Treat as NEED_MORE_INFO per the compute-optimizer-findings-auditor. Install CWAgent first. |
| `Underprovisioned` | CPU > 70% OR Memory > 80% | Proceed to Step 5 (upsize). |
| `Optimized` | All thresholds pass for current type | Proceed to Step 8 (pricing model check). |
| `NotOptimized` (insufficient data) | — | NEED_MORE_INFO: wait for additional observation. |

### Step 3: Workload classification

Classify the workload shape to guide family selection (Step 4-5):

| Workload shape | Indicators | Recommended family |
|---|---|---|
| Balanced (web server, app server, dev) | CPU ~ Memory ~ Network balanced | General purpose: m7i, m7a, m7g (Graviton), m6i, m6a |
| Compute-bound (batch, HPC, CI runners, video encoding) | CPU > Memory utilization | Compute optimized: c7i, c7a, c7g, c6i, c6a |
| Memory-bound (in-memory cache, big-data analytics, relational DB) | Memory > CPU utilization, large working set | Memory optimized: r7i, r7a, r7g, r6i, x2idn, x2iedn |
| Storage-bound (NoSQL, data warehousing, OLAP) | High disk ops, large local storage need | Storage optimized: i4i, im4gn, i4g |
| GPU (ML training/inference, rendering) | GPU utilization, CUDA workloads | GPU: g5, g6, p5, p4d |
| Network-bound (real-time streaming, HFT) | NetworkIn + NetworkOut > 50% of limit | Network optimized: c6n, m6n, r6n; or Enhanced Networking (ENA) |
| Bursty (dev/test, low-traffic web) | t-family with healthy CPUCreditBalance | Burstable: t3, t3a, t4g |

### Step 4: Downsize decision (CPU/Memory/Network/Disk all low)

Apply the downsize matrix when CPU < 30% avg AND Memory < 50% avg AND
Network < 30% of limit AND Disk < 30% of provisioned IOPS.

**Downsize magnitude:**
- If CPU < 10% AND Memory < 30%: downsize 2 sizes (e.g., m5.4xlarge → m5.large).
- If CPU < 30% AND Memory < 50%: downsize 1 size (e.g., m5.2xlarge → m5.large).
- Conservative default: downsize 1 size, observe 7 days, downsize again
  if utilization remains low. This staged approach catches edge cases
  that a 2-size jump misses.

**Family selection for downsize:**
- Prefer staying within the same family (m5.2xlarge → m5.large) for
  lowest migration risk.
- If the workload is bursty with healthy credit balance, consider
  migrating to t-family (t3/xlarge saves 60%+ vs m5.xlarge).
- If Graviton-compatible, prefer the g-suffix equivalent (m7g.large vs
  m7i.large: ~20% additional savings).

**Burstable family (t3/t3a/t4g) check:**
- Verify the workload's burst pattern: average CPU < 20% baseline (below
  credit-earning rate) and burst duration < 1 hour/day.
- If the workload sustains > 20% CPU, do NOT migrate to t-family — use
  Unlimited mode (charges for overage) or stay on m-family.

### Step 5: Upsize decision (CPU or Memory high)

Apply the upsize matrix when CPU > 70% sustained OR Memory > 80% OR
Network > 50% of limit.

**Upsize magnitude:**
- Identify the bottleneck dimension (CPU, Memory, Network, or Disk).
- Upsize to the next instance class that addresses the bottleneck:
  - CPU-bound: same family, more vCPUs (m5.large → m5.xlarge).
  - Memory-bound: switch to memory-optimized family if Memory > 80%
    persistently (m5.xlarge → r6i.xlarge, doubling memory per vCPU).
  - Network-bound: switch to network-optimized family
    (m5.xlarge → c5n.large or enable Enhanced Networking).
  - Disk-bound: migrate to storage-optimized family OR move the
    workload to EBS-optimized io2 volumes.

**Severity grading for upsizing:**
- HIGH: CPU sustained > 90% OR Memory > 95% — active performance
  degradation; upsize immediately.
- MEDIUM: CPU 70-90% OR Memory 80-95% — performance risk; upsize at
  next maintenance window.
- LOW: peaks above 70% but average < 50% — investigate via Performance
  Insights / CloudWatch before upsizing (might be a query optimization
  issue, not capacity).

### Step 6: Burstable t-family architecture change

If the current instance is t-family AND CPUCreditBalance chronically
drops below ~50 credits (visible in CloudWatch), the workload is not
burst-compatible. Two remediation paths:

1. **Enable Unlimited mode** (cheapest, preserves instance):
   `aws ec2 modify-instance-credit-specification --instance-id <id>
   --cpu-credits unlimited`. Charges for overage credits but maintains
   baseline performance. Recommended for workloads with occasional
   sustained-CPU bursts.
2. **Migrate to m-family** (most robust, higher baseline cost):
   migrate from t3.large to m6i.large (or m7g.large for Graviton).
   Eliminates the credit-balance cliff entirely. Recommended for
   workloads with sustained CPU > 20%.

### Step 7: Graviton (ARM) migration evaluation

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

### Step 8: Pricing model optimization

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

### Step 9: Impact estimation

Compute the monthly savings for each recommendation:

```
Monthly savings = (current_hourly - new_hourly) * 730 hours
```

Include EBS implications (instance-type change may unlock/include
EBS-optimization costs; current-gen instances have EBS-optimized built
in, legacy may not).

Include data transfer implications (instance-type change may have
different network performance characteristics — usually a non-issue for
same-family right-sizes, material for cross-family).

For pricing-model changes (RI/Savings Plan), compute savings separately:
```
RI savings = On-Demand hourly * (1 - RI discount) * hours
```

Total savings = rightsize savings + pricing-model savings.

### Step 10: Final verdict

The verdict is the worst-case (most-actionable) finding across all
dimensions:

- If any dimension recommends a change (downsize, upsize, architecture,
  Graviton, pricing model), verdict is **OPPORTUNITY_FOUND**.
- If all dimensions pass AND pricing is already optimized (RI/Savings
  Plan in place), verdict is **OPTIMIZED**.
- If all dimensions pass for current type but pricing model could be
  improved, verdict is **OPPORTUNITY_FOUND** (pricing dimension).
- If data is insufficient (memory absent, window < 14 days), verdict
  is **NEED_MORE_INFO**.

## Output format

```text
TARGET: <instance-id or fleet-description>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <instance-type> at <pricing-model> in <region>
  Proposed: <instance-type> at <pricing-model> in <region>
  Graviton: <yes/no/N/A>
  Family change: <yes/no>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly (rightsize): $<amount>
  Monthly (pricing model): $<amount>
  Annual total: $<amount>
  Assumptions: <list (730h/month, On-Demand baseline, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <instance-id> in <region>.
  Proceed? (yes/no)"
```

### Worked example — overprovisioned, high-confidence downsize + Graviton

```text
TARGET: i-0abc123
VERDICT: OPPORTUNITY_FOUND
REASON: m5.2xlarge at 8% CPU / 22% Memory / low Network/Disk over 30 days
  is a clear downsize candidate. Graviton-compatible workload (Java 17);
  m7g.large saves 75% on the rightsize plus 20% on Graviton price-
  performance. Adding a 3-year Compute Savings Plan captures additional
  40% on the residual spend (Step 4 + Step 7 + Step 8).
RECOMMENDATION:
  Current: m5.2xlarge at On-Demand in us-east-1
  Proposed: m7g.large at 3-year Compute Savings Plan in us-east-1
  Graviton: yes (Java 17, multi-arch AMI available)
  Family change: yes (m5 → m7g)
  Confidence: HIGH — Memory metric present (CWAgent), CPU+Memory both
    well below thresholds, Compute Optimizer cross-check agrees
    (Overprovisioned, performanceRisk 1).
ESTIMATED_SAVINGS:
  Monthly (rightsize): $232.32  (m5.2xlarge $0.384/h → m7g.large $0.0644/h;
                                 730h × $0.3196 delta)
  Monthly (pricing model): $35.96  (40% off m7g.large On-Demand via
                                    3-yr Compute Savings Plan)
  Annual total: $3,219.84
  Assumptions: 730h/month, us-east-1 On-Demand pricing as of 2026-08-07,
    workload steady-state, no significant growth expected.
MIGRATION_STEPS:
  1. Provision the new instance:
     aws ec2 run-instances --image-id <ami-arm64> --instance-type m7g.large
       --key-name <key> --security-group-ids <sg> --subnet-id <subnet>
       --tag-specifications "ResourceType=instance,Tags=[{Key=Name,
       Value=i-0abc123-m7g}]"
  2. Migrate application data / EBS volumes:
     - Create an AMI from i-0abc123 (for rollback).
     - Or attach the existing EBS volume to the new instance (requires
       stop/detach/attach).
  3. Validate application functionality on m7g.large for 24-48 hours
     (focus on memory leaks, JIT behaviour, GC pauses under load).
  4. Cutover DNS / load balancer to the new instance.
  5. Purchase a 3-year Compute Savings Plan for the m7g.large commit:
     aws savingsplans create-savings-plan --savings-plan-offering-id <id>
       --commitment <amount>
  6. Decommission i-0abc123 once the new instance is verified.
CONFIRM: Before provisioning the new instance, emit and await:
  "CONFIRM: About to run-instances m7g.large in us-east-1 for rightsize
   of i-0abc123. This will incur ~$47/month On-Demand until the Savings
   Plan is in place. Proceed? (yes/no)"
  Do NOT run the CLI until the operator confirms.
```

### Worked example — already optimal

```text
TARGET: i-0def456
VERDICT: ALREADY_OPTIMAL
REASON: c6i.4xlarge at 55% CPU / 65% Memory / 40% Network over 30 days
  is correctly sized for its workload. Already on a 3-year Compute
  Savings Plan covering 100% of the hourly spend. No Graviton
  opportunity (workload uses x86-specific SIMD intrinsics).
RECOMMENDATION:
  Current: c6i.4xlarge at 3-year Compute Savings Plan in us-east-1
  Proposed: no change
  Graviton: no (x86 SIMD intrinsics in compiled binary)
  Family change: no
  Confidence: HIGH — all utilization dimensions within healthy bands,
    Compute Optimizer finding Optimized, pricing model already optimized.
ESTIMATED_SAVINGS:
  Monthly (rightsize): $0
  Monthly (pricing model): $0
  Annual total: $0
MIGRATION_STEPS:
  - None required. Continue monitoring CloudWatch metrics monthly.
  - Re-evaluate at the Savings Plan renewal date (18 months out) for
    next-generation instance opportunities.
```

### Worked example — NEED_MORE_INFO (memory data missing)

```text
TARGET: i-0ghi789
VERDICT: NEED_MORE_INFO
REASON: MemoryUtilization metric is absent (CloudWatch Agent not
  reporting mem_used_percent). CPU at 12% suggests Overprovisioned but
  cannot be confirmed without memory data — the workload may be memory-
  bound with an idle CPU (Step 1 data gate).
RECOMMENDATION:
  Current: m5.xlarge at On-Demand in us-east-1
  Proposed: pending data
  Graviton: unknown (depends on workload type)
  Family change: pending
  Confidence: LOW — single-dimension (CPU) data only.
ESTIMATED_SAVINGS:
  Monthly (rightsize): $0 (cannot quantify without memory data)
  Monthly (pricing model): pending
MIGRATION_STEPS:
  1. Install CloudWatch Agent:
     sudo yum install amazon-cloudwatch-agent
     sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl
       -a fetch-config -m ec2 -s -c file:config.json
     (config.json must include mem_used_percent)
  2. Wait 14-30 days for representative observation.
  3. Re-evaluate with CPU + Memory + Network + Disk data.
  Do NOT right-size based on CPU-only data.
```

## Verdict semantics — reconciling the verdict_shape

The `verdict_shape` metadata declares the three primary verdicts
(`OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL`). Two additional
**data-gating** verdicts (`NEED_MORE_INFO`, `BLOCKED`) appear in the
workflow when the data required for a confident decision is missing.
Treat them as pre-decision guards, not as alternatives to the primary
three:

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one dimension (size, family, Graviton, pricing) has a concrete, savings-bearing recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | A change was applied and verified this session; metrics confirm the new size lands within healthy bands. | Primary — only emitted post-remediation. |
| `ALREADY_OPTIMAL` | All dimensions pass for the current type AND the pricing model is already committed (RI/Savings Plan covering ≥ 95% of steady-state spend). | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Data gate failed: MemoryUtilization absent, observation window < 14 days, Compute Optimizer `NotOptimized` due to insufficient data, or freshest CloudWatch signal disagrees with an old Compute Optimizer finding. | Pre-decision — emit before any sizing recommendation; the next action is data collection, not remediation. |
| `BLOCKED` | A hard precondition prevents evaluation: Compute Optimizer enrollment `Inactive` AND no CloudWatch metrics retrievable, instance is in `Stopped`/`Terminated` for > 50% of the window, or IAM denies `cloudwatch:GetMetricStatistics`. | Pre-decision — emit when no reliable signal exists at all. |

**Rule:** never emit `OPPORTUNITY_FOUND` without first discharging every
`NEED_MORE_INFO`/`BLOCKED` gate in Step 1. A downsize recommendation
that hides a missing MemoryUtilization signal is the single highest-
risk misclassification the skill can make.

## Network-limit calculation (concrete formula)

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

## Error handling — CLI and data-source failures

The workflow depends on three live data sources (CloudWatch, Compute
Optimizer, EC2 API). Each can fail independently. Handle every branch
explicitly; silent failures produce misclassifications.

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-metric-statistics` returns empty `Datapoints` array for CPUUtilization | `len(Datapoints) == 0` | Verdict: `BLOCKED`. Reason: "CloudWatch returned no CPU data for <id> over <window>. The instance may have been stopped for the entire window, or IAM denies cloudwatch:GetMetricStatistics." Recommendation: re-pull with `--start-time` shifted 1 day forward; verify IAM policy includes `cloudwatch:GetMetricStatistics` for `AWS/EC2`. |
| `mem_used_percent` absent from CWAgent namespace | `list-metrics` returns no match | Verdict: `NEED_MORE_INFO` per Step 1. Never downgrade to `OPPORTUNITY_FOUND` on CPU-only data. |
| Datapoints present but `SampleCount < 168` (less than 7 days of hourly data) | `len(Datapoints) < window_days * 24 * 0.7` | Verdict: `NEED_MORE_INFO`. Reason: "Insufficient samples (<70% of expected hourly datapoints) — observation window is not representative." |
| CloudWatch API throttling (`Throttling` error) | Exit code non-zero, stderr contains "Throttling" | Retry with exponential backoff (`--max-attempts 5`). If still failing, fall back to a 7-day window and flag the result as LOW-confidence. |

### Compute Optimizer failures

| Failure mode | Detection | Handling |
|---|---|---|
| Enrollment `Inactive` | `get-enrollment-status` returns `"status": "Inactive"` | Compute Optimizer findings are unavailable. Proceed with CloudWatch-only analysis; mark `compute_optimizer_cross_check: unavailable` in the output. Do NOT block the workflow. |
| `get-ec2-instance-recommendations` returns empty `recommendations` array | `len(recommendations) == 0` | Either the instance is Optimal (no findings) or Compute Optimizer has not yet analyzed it. Cross-check `lastRefreshTimestamp`; if > 30 days old, treat as stale and rely on CloudWatch. If recent, treat as `Optimized` from Compute Optimizer's perspective. |
| Compute Optimizer finding present but `performanceRisk` missing | Field absent in JSON | Reject the finding as LOW-confidence. Fall back to CloudWatch thresholds; do not blindly apply the recommendation. |
| `AccessDeniedException` for `compute-optimizer:*` | Exit code non-zero | Compute Optimizer is not enabled in the account or the role lacks permissions. Proceed with CloudWatch-only; surface the gap in the output. |

### EC2 API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-instance-types` returns `UnknownInstanceType` | API error | The target type (e.g., next-gen not yet rolled out in this region) is unavailable. Fall back to a documented alternative from the references/instance-selection-reference.md table. |
| `describe-instances` shows instance `Terminated` | `State.Name == "terminated"` | Skip the instance entirely. Emit no verdict; note in the fleet rollup as "terminated during evaluation." |
| `modify-instance-attribute` fails with `IncorrectInstanceState` | Instance not stopped | Stop the instance first (`stop-instances`), wait for `State.Name == "stopped"`, retry. Surface the stop/start sequence in MIGRATION_STEPS. |
| `purchase-reserved-instances-offering` fails with `InvalidParticle` | Offering ID stale or already fulfilled | Re-query `describe-reserved-instances-offerings --offering-class <standard|convertible> --instance-type <type>` to fetch a fresh offering-id. |

### Aggregate behavior

If ANY data source fails with a transient error (throttling, network),
retry up to 3 times with exponential backoff before emitting `BLOCKED`.
For persistent failures (IAM denial, terminated instance, enrollment
Inactive), emit the appropriate gating verdict and proceed with the
remaining dimensions — do not abort the entire evaluation on a single
source failure.

## Anti-Patterns — NEVER

- NEVER recommend a downsize without MemoryUtilization data. CPU is the
  visible signal; memory is the load-bearing constraint. A downsize
  based on CPU alone may crash a memory-bound workload.

- NEVER recommend Spot Instances for stateful workloads. Databases,
  message queues, singleton services, and any instance holding local
  state will lose data on Spot interruption. Spot is for stateless,
  fault-tolerant workloads only.

- NEVER assume Graviton compatibility without verification. Most JVM/
  Python/Go workloads work; C/C++ and any code with platform-specific
  binaries need recompilation. Always check `describe-instance-types`
  and the application runtime support matrix.

- NEVER recommend migrating to a t-family (t3/t3a/t4g) without checking
  the workload's burst pattern. Sustained CPU > 20% baseline will
  exhaust CPUCreditBalance and trigger the 20% baseline performance
  cliff. Use Unlimited mode or stay on m-family for sustained workloads.

- NEVER recommend a Standard RI for a workload with uncertain growth.
  Standard RIs cannot be exchanged across families. Use Convertible RI
  or Compute Savings Plan for flexibility insurance.

- NEVER assume a 30-day observation window is sufficient for seasonal
  workloads. E-commerce (holiday peaks), tax software (April), and
  education (semester starts) all have seasonal patterns invisible in
  a generic 30-day window. Pull data from peak and off-peak periods
  before right-sizing.

- NEVER right-size based on a single metric (CPU only, Memory only,
  Network only). Require at minimum CPU + Memory + one more dimension
  for HIGH-confidence downsize recommendations.

- NEVER skip the rollback plan for production right-sizes. Always
  create an AMI before stopping/modifying; always keep the original
  instance for 24-48 hours post-cutover; always document the rollback
  procedure.

- NEVER trust memorized instance specs. AWS releases new generations
  frequently; always query `aws ec2 describe-instance-types` for current
  vCPU, memory, network, and storage specs.

- NEVER recommend a Zonal RI for a workload that may need to migrate
  AZs. Zonal RIs are tied to a specific AZ; Regional RIs and Compute
  Savings Plans apply across AZs in the region. Default to Regional
  unless there's a specific capacity-reservation need.

- NEVER stack a right-size and a pricing-model change in a single step.
  Right-size first (utilization change), verify for 7 days, then
  adjust the pricing model commitment. Stacking both at once obscures
  which change produced the savings.

- NEVER recommend Compute Savings Plan commitments beyond the steady-
  state baseline. The flexible nature of Savings Plans means the
  commitment applies regardless of instance mix, but committing beyond
  steady-state leaves you paying for unused capacity. Right-size first,
  identify the steady-state, then commit.

- NEVER ignore EBS-optimization costs in legacy migrations. m4.10xlarge
  and earlier (some m4/c4 generations) charge hourly for EBS-optimized
  status; current-gen (m5+) includes it free. A migration from m4 to
  m6i unlocks "free" EBS optimization in addition to other savings.

- NEVER treat Compute Optimizer's recommendation options at rank 1 as
  the safest. Rank 1 is the cheapest (highest savings); it may carry
  the highest performanceRisk. Always check `performanceRisk` on each
  option and prefer risk ≤ 2 for production workloads.

- NEVER right-size without considering cross-AZ transfer costs. A
  right-size that moves an instance to a different AZ (via replacement)
  may shift cross-AZ data-transfer patterns. Same-AZ right-sizes have
  no transfer impact.

- NEVER recommend Unlimited mode as a permanent fix for a t-family
  workload with sustained CPU > 50%. Unlimited charges for overage
  credits indefinitely; migrating to m-family is cheaper above ~40%
  sustained utilization.

- NEVER recommend Spot without checking the Spot Placement Score (SPS)
  for the target instance type and AZ. SPS predicts the likelihood of
  Spot capacity being available; a low score (≤ 10) means Spot requests
  in that AZ/type are frequently unfulfilled or interrupted. Without
  SPS, a "90% savings" Spot recommendation may be unlaunchable in
  practice, or may interrupt so frequently that the workload fails.
  Always pull
  `aws ec2 get-spot-placement-scores --instance-types <type>
  --target-capacity 1 --region-name <region>` and surface the SPS in
  the recommendation. Prefer types with SPS ≥ 50 for production-
  adjacent Spot workloads.

- NEVER recommend a Standard RI when the workload may need to change
  instance families within the commitment term. **Why Standard RIs
  cannot be exchanged:** AWS models Standard RIs as a fixed
  reservation of a specific instance family + size + AZ (Zonal) or
  family + size (Regional). The discount is bound to that exact
  configuration for the full 1- or 3-year term because AWS uses the
  commitment to provision underlying capacity. Convertible RIs allow
  exchanges (family, size, OS, tenancy) but charge a slightly lower
  discount in exchange for the optionality. If a right-size may
  trigger a family migration (e.g., m5 → r6i for memory-bound drift),
  default to Convertible RI or Compute Savings Plan. Standard RI is
  only appropriate when the workload is locked to a single family for
  the full term (e.g., a vendor-certified appliance that pins to c6i).

- NEVER interpret Compute Optimizer `Optimized` as ALREADY_OPTIMAL
  without checking the pricing model separately. Compute Optimizer
  evaluates utilization only — it does not flag On-Demand spend that
  could move to an RI or Savings Plan. An "Optimized" instance may
  still be 100% On-Demand, missing 30-72% in commitment savings.
  Always run Step 8 (pricing model) before emitting ALREADY_OPTIMAL.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`stop-instances`, `modify-instance-attribute`, `run-instances`,
  `create-savings-plan`), emit and await operator approval. Do NOT
  execute the CLI until the operator confirms.

- **Snapshot before right-sizing.** Capture the current state:
  `aws ec2 create-image --instance-id <id> --name "pre-rightsize-$(date +%s)"`
  This provides a rollback path if the new type cannot handle the workload.

- **Verify the instance is `stopped` before type change.**
  `aws ec2 modify-instance-attribute --instance-type` requires the
  instance to be stopped. Attempting it on a running instance returns
  `IncorrectInstanceState`.

- **Right-size in off-peak hours for production.** Stop, modify, restart
  causes 2-10 minutes of downtime. Schedule outside peak traffic windows.

- **Prefer replacement to in-place modification for cross-family
  migrations.** Cross-family changes (m5 → t3, m5 → m7g) may require AMI
  changes (different architecture, different virtualization). Provision
  a new instance, validate, cutover, decommission the original — safer
  than in-place modification.

- **Savings Plan commitments are billing-account-level.** A Savings Plan
  applies to the entire payer account; committing $X/hour affects all
  instances in the account, not just the target. Surface this in the
  CONFIRMATION gate.

- **Bulk-operation safety limit.** Remediation across a fleet MUST
  follow this algorithm:
  1. Sort flagged instances by estimated savings (largest first).
  2. Slice into batches of at most 5 instances.
  3. For each batch: emit the per-instance MIGRATION_STEPS, then a
     single CONFIRM for the batch.
  4. After the operator confirms and the CLI runs, re-query with
     `aws ec2 describe-instances` and verify the new type landed
     before emitting the NEXT batch.
  5. Abort the sweep if any instance fails to restart or shows degraded
     performance in CloudWatch post-change.
  The skill MUST NOT emit remediation CLI for more than 5 instances in
  a single output block. Auto-applying across an entire fleet in one
  pass is forbidden: a single systematic misclassification cascades
  into mass disruption.

- **Verify Savings Plan coverage post-commitment.**
  `aws savingsplans describe-savings-plans --state ACTIVE` — confirm the
  commitment is active and the target instances are drawing from it.
  Savings Plans take up to 1 hour to fully propagate.

## Remediation guidance

### For OPPORTUNITY_FOUND — downsize

1. Snapshot the current instance:
   `aws ec2 create-image --instance-id <id> --name "pre-rightsize-<timestamp>"`.
2. Stop the instance: `aws ec2 stop-instances --instance-ids <id>`.
3. Change the type: `aws ec2 modify-instance-attribute --instance-id <id>
   --instance-type "{\"Value\": \"<new-type>\"}"`.
4. Start: `aws ec2 start-instances --instance-ids <id>`.
5. Monitor CPU + Memory for 7 days. Roll back if CPU > 80% or Memory > 85%.

### For OPPORTUNITY_FOUND — upsize

Same as downsize, but with a larger instance type. For memory-bound
upsizes, prefer the r-family (more memory per vCPU) over m-family if
the workload is genuinely memory-pressured.

### For OPPORTUNITY_FOUND — Graviton migration

1. Provision a new instance with an arm64 AMI:
   `aws ec2 run-instances --image-id <ami-arm64> --instance-type <new-type>`.
2. Migrate application code/data.
3. Validate for 24-48 hours (memory leaks, JIT behaviour, GC pauses).
4. Cutover DNS / load balancer.
5. Decommission the original x86 instance.

### For OPPORTUNITY_FOUND — t-family architecture change

- **Enable Unlimited mode**: `aws ec2 modify-instance-credit-specification
  --instance-id <id> --cpu-credits unlimited`. Immediate effect, no
  restart required.
- **Migrate to m-family**: same as cross-family migration (above).

### For OPPORTUNITY_FOUND — pricing model

- **Reserved Instance (Standard)**: `aws ec2 purchase-reserved-instances-offering
  --reserved-instances-offering-id <id> --instance-count 1`. Apply for
  steady-state workloads with predictable usage.
- **Reserved Instance (Convertible)**: same CLI, different offering class.
  Apply for workloads with growth uncertainty.
- **Compute Savings Plan**: `aws savingsplans create-savings-plan
  --savings-plan-offering-id <id> --commitment "<amount>"`. Apply for
  mixed fleets with flexible instance mix.
- **Spot Instances**: launch with `--instance-market-options
  "MarketType=spot,SpotOptions={SpotInstanceType=persistent,
  InstanceInterruptionBehavior=stop}"`. Apply only for fault-tolerant
  workloads.

### For ALREADY_OPTIMAL or OPTIMIZED

1. No remediation required for the current posture.
2. Recommend quarterly review of CloudWatch metrics and Compute Optimizer
   findings — workloads drift.
3. For Savings Plan renewals, re-evaluate at the renewal date for next-
   generation instance opportunities (e.g., m6i → m7i may offer 15-25%
  performance improvement at the same price).

## Deep reference: EC2 instance selection

### Instance family taxonomy (current generation, 2026)

| Family | Class | Target workload | Notable feature |
|---|---|---|---|
| m7i, m7a (x86), m7g (Graviton) | General purpose | Web/app servers, dev/test, small databases | Balanced CPU/Memory/Network |
| m6i, m6a, m6g | General purpose (prior gen) | Same as m7 | Lower cost; m7 preferred for new |
| c7i, c7a, c7g | Compute optimized | Batch, HPC, web servers, CI runners | Highest vCPU per dollar |
| r7i, r7a, r7g | Memory optimized | In-memory caches (Redis, Memcached), relational DB | High memory per vCPU |
| x2idn, x2iedn, x2iezn | Memory optimized (extreme) | SAP HANA, large in-memory analytics | Very high memory (12 TB+) |
| i4i, i4g, im4gn | Storage optimized | NoSQL (Cassandra, MongoDB), data warehousing | NVMe instance storage |
| d3, d3en | Dense storage | Hadoop, data lake | HDD-based instance storage |
| g5, g5g, g6, g6e | GPU (general) | ML inference, rendering, video encoding | NVIDIA A10G / L4 / T4G |
| p5, p4d, p3 | GPU (compute) | ML training, HPC | NVIDIA H100 / A100 / V100 |
| inf2, trn1, trn1n | Accelerator (AWS) | ML inference / training | AWS Inferentia / Trainium |
| c6n, m6n, r6n | Network optimized | HFT, real-time streaming, NFV | 100 Gbps networking |
| t3, t3a, t4g | Burstable | Dev/test, low-traffic web | CPU credit system |

### Graviton generations

| Generation | Families | Notes |
|---|---|---|
| Graviton (v1) | a1 | Deprecated; replaced by Graviton 2. |
| Graviton 2 (2020) | m6g, c6g, r6g, t4g, im4gn, x2gd | Significant price-performance jump; widely deployed. |
| Graviton 3 (2022) | c7g, r7g, m7g | DDR5 memory; up to 25% better performance than Graviton 2. |
| Graviton 4 (2024) | i8g, r8g (rolling out 2024-2026) | Further performance improvements; broader family coverage. |

### Pricing model comparison

| Model | Commitment | Discount | Flexibility | Best for |
|---|---|---|---|---|
| On-Demand | None | 0% | Highest | Spiky workloads, experiments |
| Spot | None (2 min warning) | Up to 90% | Interruptible | Stateless batch, microservices |
| Standard RI (1-yr) | 1 yr | ~40% | Zonal or Regional; fixed family | Predictable steady-state |
| Standard RI (3-yr) | 3 yr | ~60% | Zonal or Regional; fixed family | Long-term steady-state |
| Convertible RI (1-yr) | 1 yr | ~30% | Exchangeable across families | Workloads with growth |
| Convertible RI (3-yr) | 3 yr | ~55% | Exchangeable across families | Long-term with flexibility |
| Compute Savings Plan (1-yr) | 1 yr | ~30% | Any family, region, OS | Mixed fleets |
| Compute Savings Plan (3-yr) | 3 yr | ~50% | Any family, region, OS | Mixed fleets (long-term) |
| Instance Savings Plan (1-yr) | 1 yr | ~35% | Specific family + region | Family-steady fleets |
| Instance Savings Plan (3-yr) | 3 yr | ~55% | Specific family + region | Family-steady fleets (long-term) |

### Burstable (t-family) credit math

```
Earn rate (credits/hour) = instance vCPUs * 6
Spend rate (credits/hour) = CPU utilization % / 100 * vCPUs * 60
Net credit change per hour = earn rate - spend rate
```

Example: t3.large (2 vCPUs) at 50% sustained CPU:
- Earn: 2 * 6 = 12 credits/hour
- Spend: 50% / 100 * 2 * 60 = 60 credits/hour
- Net: -48 credits/hour (credit balance depletes)

Below the credit-balance floor, performance drops to ~20% baseline (12%
of full CPU on a 2-vCPU t3.large). Enable Unlimited mode or migrate to
m-family.

### Network performance tiers

| Instance class | Network performance | Notes |
|---|---|---|
| nano / micro | "Up to 0.064 Gbps" | Burstable, low ceiling |
| small / medium | "Up to 0.256 / 0.5 Gbps" | Burstable, modest |
| large (m5/c5/r5) | "Up to 10 Gbps" | Burstable, sufficient for most |
| xlarge+ (m5.2xlarge+) | "Up to 12.5 Gbps" | Higher burst ceiling |
| n-family (c6n/m6n/r6n) | 25-100 Gbps guaranteed | Network-optimized |
| 7th-gen large+ (m7i/c7i) | "Up to 12.5 Gbps" (better burst) | Improvement over 5th-gen |

"Up to X" means burst, not guaranteed. Sustained high network traffic
should use n-family or 7th-gen for guaranteed bandwidth.

## Recent AWS features (2024-2026)

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

## Domain

AWS CloudOps / EC2 Compute Cost Optimization, FinOps & Right-Sizing.

## AWS documentation

- **Amazon EC2 User Guide — Instance types** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html
- **AWS Compute Optimizer User Guide** — https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is.html
- **AWS CloudWatch Agent User Guide** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html
- **AWS Savings Plans User Guide** — https://docs.aws.amazon.com/savingsplans/latest/userguide/
- **Amazon EC2 pricing** — https://aws.amazon.com/ec2/pricing/
- **AWS Graviton** — https://aws.amazon.com/ec2/graviton/
- **AWS CLI EC2 reference** — https://docs.aws.amazon.com/cli/latest/reference/ec2/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
