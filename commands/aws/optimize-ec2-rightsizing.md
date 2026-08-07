---
description: Right-size EC2 instances for cost optimization — applies the decision matrix (CPU/Memory/Network/Disk thresholds), interprets Compute Optimizer findings, evaluates Graviton migration, and recommends pricing-model optimizations (RI/Savings Plans/Spot) with monthly savings estimates.
nl_triggers:
  - "right-size EC2 instances"
  - "EC2 cost optimization"
  - "Compute Optimizer EC2 recommendations"
  - "EC2 underutilized"
  - "EC2 overprovisioned"
  - "FinOps EC2 savings"
  - "Graviton migration opportunity"
  - "EC2 Reserved Instance"
  - "Savings Plan recommendation"
  - "EC2 instance family selection"
  - "EC2 monthly savings estimate"
  - "EC2 fleet rightsizing"
  - "t-family CPU credit exhaustion"
  - "m5 to m7i migration"
  - "EC2 pricing model optimization"
  - "spot instance opportunity"
  - "EC2 downsize recommendation"
  - "EC2 upsize recommendation"
routes_to: ec2-rightsizing-optimizer
---

# /aws:optimize-ec2-rightsizing

Activate the `ec2-rightsizing-optimizer` skill and right-size EC2
instances for cost optimization using the utilization-driven decision
matrix.

## What it does

Reads an EC2 instance's utilization data (14-30 day CloudWatch metrics
including the load-bearing MemoryUtilization from the CloudWatch Agent)
plus optional Compute Optimizer findings, then applies the ordered
optimization logic:

1. **Pre-flight** — data sufficiency gate. If `MemoryUtilization` is
   absent, emits NEED_MORE_INFO (install CWAgent, wait 14-30 days).
2. **Workload classification** — balanced, compute-bound, memory-bound,
   storage-bound, GPU, network-bound, bursty.
3. **Decision matrix**:
   - CPU < 30% + Memory < 50% → downsize 1-2 sizes.
   - CPU > 70% sustained OR Memory > 80% → upsize.
   - Burstable t-family with chronic CPUCreditBalance depletion →
     Unlimited mode or migrate to m-family.
   - Network-bound → n-family or Enhanced Networking.
4. **Graviton evaluation** — verify ARM compatibility (JVM/Python/Go/
   container workloads typically compatible; C/C++/assembly typically
   not), recommend m7g/c7g/r7g for up to 40% better price-performance.
5. **Pricing model optimization** — On-Demand → RI (Standard/Convertible,
   1/3yr) or Compute/Instance Savings Plan; Spot for fault-tolerant
   workloads.
6. **Impact estimation** — monthly + annual savings, assumptions
   documented.
7. **Verdict** — OPPORTUNITY_FOUND (any dimension has a recommendation),
   OPTIMIZED (all dimensions pass, pricing already optimized), or
   ALREADY_OPTIMAL (no change recommended).

Emits a deterministic optimization block per instance:

```text
TARGET: <instance-id or fleet-description>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <instance-type> at <pricing-model> in <region>
  Proposed: <instance-type> at <pricing-model> in <region>
  Graviton: <yes/no/N/A>
  Family change: <yes/no>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly (rightsize): $<amount>
  Monthly (pricing model): $<amount>
  Annual total: $<amount>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste an EC2 instance's utilization data and ask any of:

- "right-size this EC2 instance"
- "should I migrate to Graviton?"
- "is this Compute Optimizer finding actionable?"
- "what RI or Savings Plan should I buy?"
- "EC2 fleet cost optimization review"
- "should I use Spot for this workload?"
- "is my t3.large running out of CPU credits?"

A bare instance ID + any optimization verb ("optimize this instance",
"cost review") also routes here via the orchestrator.

## Inputs

- Instance metadata: instance ID, current type, region, current pricing
  model (On-Demand / RI / Savings Plan / Spot).
- Utilization metrics (last 14-30 days):
  - `CPUUtilization` (CloudWatch, always available)
  - `MemoryUtilization` (CloudWatch Agent, required for downsize
    recommendations)
  - `NetworkIn`, `NetworkOut` (CloudWatch, always available)
  - `DiskReadOps`, `DiskWriteOps` (CloudWatch, for instance-store
    workloads)
  - `CPUCreditBalance` (for t-family instances)
- Optional: Compute Optimizer EC2 finding document (finding,
  findingReasons, utilizationMetrics, recommendationOptions).
- Optional: workload context (runtime, OS, AMI architecture, Docker
  image manifest) for Graviton compatibility check.

## Outputs

- One optimization block per instance.
- Confidence level with rationale (HIGH requires Memory metric +
  Compute Optimizer cross-check + clear thresholds).
- Estimated monthly and annual savings, broken down by rightsize and
  pricing model.
- Specific migration steps with CLI commands (run-instances for cross-
  family, modify-instance-attribute for same-family, create-savings-plan
  for pricing-model).
- Rollback path (pre-rightsize AMI) for production right-sizes.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for EC2 compute cost).
- `/aws:audit-compute-optimizer-findings` to audit the confidence of a
  specific Compute Optimizer finding before acting on it.
- `/aws:audit-ebs-volume` for EBS volume cost optimization (storage
  rather than compute).
