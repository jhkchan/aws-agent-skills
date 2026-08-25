---
name: ec2-instance-rightsizer
description: Right-sizes EC2 instances for cost optimization using a utilization-driven decision matrix across CPU, memory, network, and disk. Analyses 14-30 day CloudWatch utilization (CPUUtilization, NetworkIn/Out, DiskReadOps) plus CloudWatch agent memory metrics (MemoryUtilization, mem_used_percent), interprets Compute Optimizer EC2 recommendations, detects idle instances (<5% CPU for 14 consecutive days), evaluates instance-family migration paths (m5 to m6i/m7i, c5 to c7g, r5 to r7g), assesses Graviton (arm64) AMI and application compatibility, tunes burstable instances (t3/t4g Unlimited vs default credit mode), applies workload-specific sizing rules (web server vs database vs batch), accounts for Savings Plans impact on right-sizing decisions, and checks termination protection before any resize action. Emits OPTIMIZED when all dimensions pass, or FURTHER_OPTIMIZATION_AVAILABLE when a concrete downsize, upsize, family migration, or Graviton opportunity exists with a dollar savings estimate.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted CloudWatch metrics and Compute Optimizer findings. Live-account optimization uses aws ec2 describe-instances, aws ec2 describe-instance-attribute, aws cloudwatch get-metric-statistics (CPUUtilization, NetworkIn, NetworkOut, DiskReadOps, DiskWriteOps), aws cloudwatch list-metrics (CWAgent memory namespace), aws compute-optimizer...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Right-sizing EC2 instances for cost, triaging Compute Optimizer EC2 findings, evaluating Graviton (arm64) migration, tuning burstable t3/t4g instances (Unlimited vs default), detecting idle EC2 instances (<5% CPU sustained), planning instance-family migrations (m5 to m6i/m7i, c5 to c7g), or running a FinOps EC2 right-sizing sweep.
  when_not_to_use: EC2 Reserved Instance or Savings Plan purchasing decisions (use ec2-reserved-capacity-optimizer), EBS volume cost optimization (use ebs-volume-optimizer), EC2 security group auditing (use ec2-security-group-auditor), or EC2 launch troubleshooting (use the EC2 troubleshooter). This skill focuses on instance-type right-sizing, not pricing-model procurement or functional debugging.
  activation_triggers: right-size EC2 instance, EC2 cost optimization, EC2 Compute Optimizer recommendation, EC2 underutilized, EC2 overprovisioned, EC2 idle detection, EC2 Graviton migration, EC2 arm64 compatibility, EC2 instance family migration, m5 to m6i migration, c5 to c7g migration, t3 Unlimited vs default, t4g CPU credits, EC2 CPU utilization low, EC2 memory utilization, EC2 FinOps right-sizing, EC2 workload sizing, EC2 downsize recommendation, EC2 upsize recommendation, Savings Plans right-sizing impact
  invocation_schema: 'Input: either (a) an instance ID or fleet description + live-account context, (b) a Compute Optimizer EC2 finding document, OR (c) CloudWatch utilization metrics (CPUUtilization, NetworkIn/Out, DiskReadOps, MemoryUtilization from CWAgent) with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS block per instance, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline finding classification):\nInstanceId: i-0abc123def456\nInstanceType: m5.2xlarge\nArchitecture: x86_64\nRegion: us-east-1\nPricing: On-Demand (no\n Savings Plan coverage)\nMetrics (last 14 days):\n  - CPUUtilization avg: 3.2%, p95: 7.1%\n  - MemoryUtilization avg: 28% (CWAgent mem_used_percent)\n  - NetworkIn avg: 12 MB/h\n  - DiskReadOps avg: 450/s\nCompute Optimizer finding: Overprovisioned\nEmit the standard right-sizing block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EC2, right-sizing, cost optimization, Compute Optimizer, CloudWatch utilization, CPUUtilization, MemoryUtilization, CWAgent, idle instance, instance family migration, m5 to m6i, c5 to c7g, Graviton, arm64, Graviton2, burstable, t3 Unlimited, t4g, CPU credits, CPUCreditBalance, workload sizing, web server, database, batch, Savings Plans, Spot, termination protection, FinOps
  tags: ec2, compute, cost-optimization, finops, rightsizing, graviton, compute-optimizer
---

# EC2 Instance Rightsizer

## What this skill does

Translates an EC2 instance's utilization posture into a concrete right-
sizing recommendation with a dollar-denominated savings estimate. The
verdict is the highest-leverage action across seven dimensions — idle
detection, CPU/memory utilization, instance-family migration, Graviton
(arm64) compatibility, burstable credit behavior, workload-specific
sizing, and Savings Plan impact — applied in priority order. Always
pairs the recommendation with exact CLI commands and a termination-
protection safety gate.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the expert principle | First read |
| Mindset | Why utilization + Compute Optimizer + workload context | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying an instance |
| Pre-flight data gate | CloudWatch + CWAgent + Compute Optimizer | Before any recommendation |
| Step 0 non-obvious behaviours | CWAgent memory, credit exhaustion, Savings Plans | Edge cases |
| Step 1 Idle detection | <5% CPU for 14 days, hibernate vs stop | The zero-utilization dimension |
| Step 2 CPU + memory utilization | Downsize/upsize thresholds | The headline savings dimension |
| Step 3 Instance-family migration | m5 to m6i/m7i, c5 to c7g, same-arch upgrades | Cross-family savings |
| Step 4 Graviton (arm64) | AMI + application compatibility testing | 20-40% price-performance |
| Step 5 Burstable instances | t3/t4g Unlimited vs default, credit exhaustion | t-family tuning |
| Step 6 Workload-specific sizing | Web server vs database vs batch | Workload-aware rules |
| Step 7 Savings Plans + pricing | How commitments affect right-sizing | Commitment-aware decisions |
| Step 8 Spot vs on-demand | Interruptible workload evaluation | Fault-tolerant workloads |
| Step 9 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | Termination protection, CONFIRM gate | Before any apply CLI |

## Quick start

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Mindset

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| CPUUtilization avg < 5% for 14+ consecutive days AND NetworkIn < 10 MB/h AND DiskReadOps < 100/s | **FURTHER_OPTIMIZATION_AVAILABLE** (idle) | Step 1 — stop or terminate (downsize if must stay up) |
| CPU avg < 30% AND MemoryUtilization < 50% (CWAgent confirmed) | **FURTHER_OPTIMIZATION_AVAILABLE** (downsize) | Step 2 — downsize 1-2 sizes within family |
| CPU avg > 70% sustained OR MemoryUtilization > 85% | **FURTHER_OPTIMIZATION_AVAILABLE** (upsize) | Step 2 — upsize within or across family |
| Compute Optimizer finding `Overprovisioned` with findingReasons citing low CPU/memory | **FURTHER_OPTIMIZATION_AVAILABLE** (downsize) | Step 2 — cross-check with CloudWatch, apply |
| Instance on x86_64 AND workload is Graviton-compatible (JVM, Python, Go, Node, container) | **FURTHER_OPTIMIZATION_AVAILABLE** (Graviton) | Step 4 — migrate to c7g/m7g/r7g after AMI + app testing |
| t3/t4g instance AND CPUCreditBalance trending to 0 AND CPU credits exhausted > 3 days | **FURTHER_OPTIMIZATION_AVAILABLE** (burstable) | Step 5 — enable Unlimited or migrate to m-family |
| Instance 2+ generations old (m4, c4, r4, t2) | **FURTHER_OPTIMIZATION_AVAILABLE** (generation) | Step 3 — migrate to current-gen (m6i/m7i, c6i/c7i) |
| All dimensions verified AND instance is current-gen AND right-sized AND no Graviton opportunity | **OPTIMIZED** | None — continue monitoring |
| MemoryUtilization absent (CWAgent not installed) AND CPU < 30% | **NEED_MORE_INFO** | Install CWAgent, wait 14 days, re-evaluate |
| Observation window < 14 days | **NEED_MORE_INFO** | Minimum 14 days; 30 days preferred |

## Pre-flight: data gate (run before any optimization decision)

Right-sizing decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/ec2-pricing-and-instance-matrix.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Instance configuration: `aws ec2 describe-instances` (type, AMI,
   architecture, tags, state, placement)
2. Termination protection: `aws ec2 describe-instance-attribute
   --attribute disableApiTermination`
3. CPUUtilization + NetworkIn/Out + DiskReadOps (14-30 day window):
   `aws cloudwatch get-metric-statistics --namespace AWS/EC2`
4. MemoryUtilization (CWAgent): `aws cloudwatch get-metric-statistics
   --namespace CWAgent` (metric: `mem_used_percent`)
5. CPUCreditBalance (t-family): `aws cloudwatch get-metric-statistics`
   for `CPUCreditBalance`
6. Compute Optimizer findings: `aws compute-optimizer
   get-ec2-instance-recommendations`
7. Savings Plan coverage: `aws savingsplans describe-savings-plans`
   (active plans that affect the right-sizing math)

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `CPUUtilization` metric absent (instance stopped) | **NEED_MORE_INFO**. Verify instance state; skip until running. |
| `MemoryUtilization` (CWAgent) absent | **NEED_MORE_INFO** for downsize recommendations. Upsize can proceed on CPU alone with MEDIUM confidence. |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| Compute Optimizer enrollment `Inactive` | Proceed with CloudWatch directly. Surface that cross-check is unavailable. |
| Compute Optimizer `lastRefreshTimestamp` > 30 days old | Stale finding. Re-run `get-ec2-instance-recommendations`. |
| Instance `State != running` | Skip optimization; surface as BLOCKED. |
| `disableApiTermination = true` | Surface as a gate for stop/terminate actions. Do NOT override. |
| Spot instance with interruption | Right-sizing still applies, but note that Spot pricing volatility changes the savings math. |

When CloudWatch and Compute Optimizer disagree, **workload context is
the tiebreaker**. A database with low CPU but high memory utilization
is NOT a downsize candidate regardless of what Compute Optimizer says.

## Process — Right-sizing logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 1: Idle instance detection (<5% CPU for 14 days)

An idle instance is the highest-savings right-sizing target because the
recommendation is stop or terminate — 100% of the compute cost is
eliminated.

**Idle detection criteria (ALL must be true for 14 consecutive days):**
```
CPUUtilization avg < 5%
NetworkIn avg < 10 MB/hour
NetworkOut avg < 10 MB/hour
DiskReadOps avg < 100 ops/s
DiskWriteOps avg < 100 ops/s
```

**Decision tree for idle instances:**
```
Is the instance tagged as production or critical?
├── YES → Do NOT stop/terminate. Downsize to smallest viable type
│         (e.g., t3.nano) and surface as "verify with owner."
└── NO → Is the instance EBS-backed?
    ├── YES → Recommend STOP (not terminate). Preserves the root
    │         volume for restart. Savings: 100% of compute.
    └── NO (instance-store) → Recommend SNAPSHOT then TERMINATE.
              Instance-store root volumes are lost on stop.

Is termination protection enabled?
├── YES → Surface as gate: "disableApiTermination must be set to false
│         before termination." Provide the CLI but do NOT execute.
└── NO → Proceed with stop/terminate recommendation.
```

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 2: CPU + memory utilization analysis

This is the core right-sizing dimension: matching instance size to
observed utilization.

**Downsize thresholds (ALL must be true):**
```
CPUUtilization avg < 30% AND p95 < 50%
MemoryUtilization avg < 50% (CWAgent required)
NetworkIn/Out: not saturating instance limits
DiskReadOps/WriteOps: not saturating instance limits
```

**Upsize thresholds (ANY triggers evaluation):**
```
CPUUtilization avg > 70% OR p95 > 90%
MemoryUtilization avg > 80% OR peaks > 90% (CWAgent)
CPUCreditBalance trending to 0 (t-family only)
NetworkIn/Out consistently > 60% of instance capacity
```

**Downsize path (within same family + generation):**
```
m5.2xlarge  (8 vCPU, 32 GB) → m5.xlarge (4 vCPU, 16 GB)  if CPU < 20%, Mem < 40%
m5.xlarge   (4 vCPU, 16 GB) → m5.large   (2 vCPU, 8 GB)  if CPU < 15%, Mem < 30%
c5.4xlarge  (16 vCPU, 32 GB) → c5.2xlarge (8 vCPU, 16 GB) if CPU < 20%, Mem < 40%
r5.2xlarge  (8 vCPU, 64 GB) → r5.xlarge  (4 vCPU, 32 GB) if CPU < 20%, Mem < 35%
```

Always verify that the target instance type has enough memory for the
workload's peak usage (including OS overhead ~5-10% of RAM).

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 3: Instance-family migration (same architecture)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).
Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 4: Graviton (arm64) migration

Graviton2 (and Graviton3) processors deliver up to 40% better price-
performance than comparable x86 instances. However, migration requires
an arm64 AMI and application-level compatibility testing.

Moved verbatim to [references/ec2-pricing-and-instance-matrix.md](references/ec2-pricing-and-instance-matrix.md) - load on demand (see References below).

**Compatibility decision tree:**
```
Is the workload JVM-based (Java, Scala, Kotlin)?
├── YES → HIGH compatibility. JVM is architecture-agnostic.
│         Verify no JNI with x86 native libs. Migrate.
├── NO → Is it interpreted (Python, Ruby, Node.js)?
│   ├── YES → HIGH compatibility for pure-interpreted code.
│   │         Verify C extensions have arm64 wheels/builds.
│   │         (numpy, Pillow, psycopg2 — all have arm64 support.)
│   └── NO → Is it compiled (Go, Rust, .NET)?
│       ├── YES → Recompile for arm64 (GOARCH=arm64, rustc target).
│       │         Go and Rust have excellent cross-compilation support.
│       └── NO → Is it C/C++ or assembly?
│           ├── YES → Requires recompilation + thorough testing.
│           │         Watch for x86 intrinsics, inline assembly,
│           │         endianness assumptions. MEDIUM-HIGH risk.
│           └── NO → Is it a Docker container?
│               ├── Multi-arch image? → Pull arm64 variant.
│               └── Single-arch (amd64)? → Rebuild for arm64.
```

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

### Step 5: Burstable instances (t3/t4g)

Burstable instances (t3, t4g) earn CPU credits at a baseline rate and
can burst above baseline by spending accumulated credits. When credits
run out, the instance is throttled to baseline performance.

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

**Decision tree for t-family:**
```
Is CPUCreditBalance sustained > 100 over 14 days?
├── YES → Instance is not bursting. It may be overprovisioned.
│         Evaluate downsize (t3.large → t3.medium) or migrate to
│         m-family for flat performance.
└── NO → Is CPUCreditBalance trending to 0?
    ├── YES → Instance is credit-starved. Two options:
    │   ├── Enable T3/T4G Unlimited (borrows future credits at
    │   │   $0.05/vCPU-hour). Good for SPIKING workloads.
    │   └── Migrate to m-family (m6i.large) for consistent CPU.
    │       Good for SUSTAINED high-CPU workloads.
    └── NO → Credits are stable. Instance is well-sized.
```

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

### Step 6: Workload-specific sizing rules

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 7: Savings Plans and pricing model impact

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 8: Spot vs on-demand for interruptible workloads

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).
Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

### Step 9: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost = current_hourly_rate × 730
projected_monthly_cost = proposed_hourly_rate × 730
monthly_saving = current_monthly_cost - projected_monthly_cost

If Savings Plan covers the instance:
  current_effective_hourly = current_od_hourly × (1 - SP_discount)
  projected_effective_hourly = proposed_od_hourly × (1 - SP_discount)
  monthly_saving = (current_effective_hourly - projected_effective_hourly) × 730
```

Always state assumptions: pricing region, on-demand vs Spot vs
committed rate, 730 hours/month standard, and whether the Savings Plan
discount applies to the proposed type.

### Step 10: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass (current-gen, right-sized, no Graviton gain,
  credits stable, no idle behavior) → **OPTIMIZED**.
- Data insufficient (no CWAgent memory, window < 14 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO` gate.

## Output format

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

Full worked examples (downsize, Graviton migration, burstable tuning,
already-optimized, idle detection) are in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
TARGET: <instance-id> (<instance-type>)
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <instance-type>, <architecture>, <pricing-model>, <region>
  Proposed: <instance-type>, <architecture>, <pricing-model>, <region>
  Dimensions changed: <idle | cpu-mem | family | graviton | burstable | workload | pricing | spot>
  Dimensions checked: <list ALL, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST reflect SP/RI discount if covered
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Monthly saving: $0.00`.** If every dimension nets zero cost delta,
   the verdict MUST be `OPTIMIZED`.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend a downsize without citing CWAgent memory data or
   explicitly flagging MEDIUM/LOW confidence.** CPU alone is
   insufficient for downsize — the workload may be memory-bound.

5. **NEVER recommend a Graviton migration without verifying AMI and
   application compatibility.** Surface the arm64 AMI requirement and
   compatibility test as mandatory MIGRATION_STEPS.

6. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all dimensions, each marked
   ✓ (no finding) or → (finding).

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

8. **NEVER recommend stop/terminate on an instance with
   `disableApiTermination = true` without surfacing the gate.** The
   protection flag is a hard stop — surface it, do not override it.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: i-0abc123def456 (m5.2xlarge)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: m5.2xlarge averaging 3.2% CPU and 28% memory (CWAgent confirmed)
  over 14 days is significantly overprovisioned. Compute Optimizer
  cross-check agrees (Overprovisioned, recommends m5.large). Combined
  with a generation upgrade (m5 to m6i), monthly cost drops 75% while
  projected CPU remains under 15%.
RECOMMENDATION:
  Current: m5.2xlarge, x86_64, On-Demand, us-east-1
  Proposed: m6i.large, x86_64, On-Demand, us-east-1
  Dimensions changed: cpu-mem (downsize) + family (generation upgrade)
  Dimensions checked: idle ✓ (>5% CPU, has traffic)  cpu-mem → (3.2%/28%)
    family → (m5 to m6i)  graviton ✓ (x86 app with JNI, not migrating)
    burstable ✓ (not t-family)  workload ✓ (web server, downsize-safe)
    pricing ✓ (On-Demand, no SP to account for)  spot ✓ (production, not Spot)
  Confidence: HIGH — CWAgent memory confirms 28% avg; Compute Optimizer
    agrees; web server workload tolerates downsize; 14-day window.
ESTIMATED_SAVINGS:
  Current monthly: $280.32
    m5.2xlarge: $0.384/h × 730 = $280.32
  Projected monthly: $70.10
    m6i.large: $0.0960/h × 730 = $70.08
  Monthly saving: $210.24
    ($280.32 − $70.08 = $210.24 ✓)
  Annual saving: $2,522.88
MIGRATION_STEPS:
  1. Stop the instance:
     aws ec2 stop-instances --instance-ids i-0abc123def456
  2. Change instance type (same architecture, generation upgrade):
     aws ec2 modify-instance-attribute --instance-id i-0abc123def456 \
       --instance-type "{\"Value\": \"m6i.large\"}"
  3. Start and verify:
     aws ec2 start-instances --instance-ids i-0abc123def456
  4. Monitor CPUUtilization and MemoryUtilization for 7 days post-change.
CONFIRM: About to modify-instance-attribute on i-0abc123def456
  (m5.2xlarge → m6i.large). Monthly saving $210.24 (75%); projected CPU
  under 15%. Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?
- [ ] CWAgent memory cited (or confidence explicitly MEDIUM/LOW)?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation (downsize, upsize, family migration, Graviton, burstable fix, Spot switch). |
| `OPTIMIZED` | All dimensions pass: current-gen, right-sized for CPU+memory, no Graviton gain, credits stable, no idle behavior, pricing model appropriate. |
| `NEED_MORE_INFO` | Data gate failed: CWAgent memory absent (for downsize candidates), window < 14 days, or Compute Optimizer stale with no CloudWatch fallback. |
| `BLOCKED` | Hard precondition prevents evaluation: instance stopped, IAM denies ec2:DescribeInstances, termination protection blocks stop/terminate. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `OPTIMIZED`, never `FURTHER_OPTIMIZATION_AVAILABLE`.

## Anti-Patterns — NEVER (top 7)

1. **NEVER recommend a downsize based on CPU utilization alone without
   CWAgent memory data.** A database at 3% CPU may be using 85% of RAM
   for buffer cache. Downsizing causes OOM or cache thrashing. The
   expert rule: 14-day CPU < 5% + CWAgent memory < 50% = downsize
   candidate.

2. **NEVER recommend a Graviton migration without verifying AMI
   availability and application compatibility.** Graviton requires an
   arm64 AMI and architecture-compatible application stack. Surface the
   AMI requirement and testing steps as mandatory migration steps.

3. **NEVER enable T3/T4G Unlimited without checking whether the
   workload is spiking or sustained-high.** Unlimited for sustained
   high CPU is MORE expensive than migrating to m-family (consistent
   CPU is cheaper than borrowing credits at $0.05/vCPU-hour).

4. **NEVER recommend stop/terminate on an instance with termination
   protection enabled without surfacing the gate.** Provide the
   `disableApiTermination` CLI but do NOT execute it without operator
   approval.

5. **NEVER migrate across instance families (m5 to c5) without checking
   active Savings Plan / RI coverage.** Cross-family migration may
   orphan an existing commitment, creating a hidden cost.

6. **NEVER downsize a production database based on low CPU alone.**
   Database buffer cache uses memory regardless of CPU load. Downsizing
   memory reduces cache hit ratio, cascading into disk I/O and latency
   regression.

7. **NEVER right-size based on less than 14 days of data.** Short
   windows capture atypical load (deploy spikes, month-end batches,
   incident response). 14 days minimum, 30 days preferred.

Extended anti-patterns in `references/worked-examples.md`.

## Pre-flight safety checks (run before any remediation CLI)

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References

- `references/ec2-pricing-and-instance-matrix.md` — pricing tables,
  instance family comparison, generation migration paths, Graviton
  compatibility matrix, CWAgent metric reference, workload sizing
  rules, regional pricing multipliers, cost calculation worked examples.
- `references/worked-examples.md` — full worked examples (downsize
  within family, generation upgrade, Graviton migration, burstable
  credit fix, idle instance stop, already-optimized, NEED_MORE_INFO,
  end-to-end walkthrough), plus error handling, edge cases (ASG,
  Docker, databases), extended NEVER list, and the right-sizing
  decision tree.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Quick start rules, Mindset, Step 0 expert behaviours, hibernation table, confidence levels, Step 3/6/7/8 deep-dives, and 2024-2026 features, moved verbatim from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 3/4/5/8 CLI listings and the pre-flight safety checks, moved verbatim from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — extended with the Output format template moved verbatim from SKILL.md
- [references/ec2-pricing-and-instance-matrix.md](references/ec2-pricing-and-instance-matrix.md) — extended with the Graviton instance families table moved verbatim from SKILL.md

## Domain

AWS CloudOps / EC2 Compute Cost Optimization & FinOps Right-Sizing.

## AWS documentation

- **Amazon EC2 User Guide** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html
- **EC2 instance types** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html
- **AWS Graviton** — https://docs.aws.amazon.com/graviton/
- **Burstable performance instances** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances.html
- **AWS Compute Optimizer** — https://docs.aws.amazon.com/compute-optimizer/latest/ug/ec2.html
- **CloudWatch Agent** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html
- **EC2 Spot Instances** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html
- **Savings Plans** — https://docs.aws.amazon.com/savingsplans/latest/userguide/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
- **EC2 hibernation** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Hibernate.html
- **AWS CLI EC2 reference** — https://docs.aws.amazon.com/cli/latest/reference/ec2/
