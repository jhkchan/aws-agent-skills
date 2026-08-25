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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Mindset

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Philosophy

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 1: Validate input and data sufficiency

If `MemoryUtilization` is absent from the input metrics (CWAgent not
installed), emit NEED_MORE_INFO with a specific installation instruction:

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

If the observation window is < 14 days, emit NEED_MORE_INFO: "Observation
window is N days; minimum 14 days required for representative data."
Proceed only if both conditions are met.

### Step 2: Compute Optimizer reconciliation

If a Compute Optimizer finding is provided, reconcile with CloudWatch
metrics. Compute Optimizer's 30-day analysis is a sanity check; the
fresh CloudWatch signal wins on disagreement.

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 8: Pricing model optimization

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Worked example — NEED_MORE_INFO (memory data missing)

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Error handling — CLI and data-source failures

Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).

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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

## Remediation guidance

Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).

## Deep reference: EC2 instance selection

Moved verbatim to [references/instance-selection-reference.md](references/instance-selection-reference.md) - load on demand (see References below).

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Quick start rules, Mindset, Philosophy, Step 0 expert behaviours, Step 7 Graviton and Step 8 pricing deep-dives, network-limit formula, and 2024-2026 features, moved verbatim from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples (already optimal, NEED_MORE_INFO memory-missing) and the Step 1 NEED_MORE_INFO emit template, moved verbatim from SKILL.md
- [references/error-handling.md](references/error-handling.md) — CloudWatch/Compute Optimizer/EC2 API failure tables and per-verdict remediation guidance, moved verbatim from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight data-source CLI, Compute Optimizer parsing, and pre-flight safety checks, moved verbatim from SKILL.md
- [references/instance-selection-reference.md](references/instance-selection-reference.md) — extended with the instance family taxonomy, Graviton generations, pricing comparison, credit math, and network tiers, moved verbatim from SKILL.md

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
