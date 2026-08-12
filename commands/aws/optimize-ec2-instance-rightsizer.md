---
description: Right-size EC2 instances for cost optimization using a utilization-driven decision matrix (CPU, memory, network, disk), Compute Optimizer cross-check, Graviton (arm64) migration evaluation, burstable t-family credit analysis, workload-specific sizing rules, and Savings Plan impact with monthly savings estimates.
nl_triggers:
  - "right-size EC2 instance"
  - "EC2 cost optimization"
  - "EC2 Compute Optimizer recommendation"
  - "EC2 underutilized"
  - "EC2 overprovisioned"
  - "EC2 idle detection"
  - "EC2 Graviton migration"
  - "EC2 arm64 compatibility"
  - "EC2 instance family migration"
  - "m5 to m6i migration"
  - "c5 to c7g migration"
  - "t3 Unlimited vs default"
  - "t4g CPU credits"
  - "EC2 CPU utilization low"
  - "EC2 memory utilization"
  - "EC2 FinOps right-sizing"
  - "EC2 workload sizing"
  - "EC2 downsize recommendation"
  - "EC2 upsize recommendation"
  - "Savings Plans right-sizing impact"
routes_to: ec2-instance-rightsizer
---

# /aws:optimize-ec2-instance-rightsizer

Activate the `ec2-instance-rightsizer` skill and right-size EC2
instances for cost optimization using the utilization-driven decision
matrix.

## What it does

Reads an EC2 instance's utilization data (14-30 day CloudWatch metrics
including the load-bearing MemoryUtilization from the CloudWatch Agent)
plus optional Compute Optimizer findings, then applies the ordered
optimization logic:

1. **Pre-flight** — data sufficiency gate. If `MemoryUtilization`
   (CWAgent `mem_used_percent`) is absent and a downsize is being
   considered, emits NEED_MORE_INFO. If the observation window < 14
   days, emits NEED_MORE_INFO.
2. **Idle detection** — CPU < 5% for 14 consecutive days with negligible
   network and disk I/O. Recommend stop or terminate (check termination
   protection first).
3. **CPU + memory utilization** — downsize if CPU < 30% AND memory <
   50% (CWAgent). Upsize if CPU > 70% OR memory > 85%.
4. **Instance-family migration** — generation upgrade (m5 to m6i/m7i,
   c5 to c6i/c7i) for 10-30% price-performance gain at the same size.
5. **Graviton (arm64) evaluation** — verify AMI + application
   compatibility (JVM/Python/Go/Node/container = compatible; C/C++ =
   recompile). Recommend m7g/c7g/r7g for up to 20% cost saving + 20%
   performance gain.
6. **Burstable instances** — t3/t4g with CPUCreditBalance trending to
   0: enable Unlimited for spiking workloads, migrate to m-family for
   sustained-high workloads.
7. **Workload-specific sizing** — web server (downsize-safe), database
   (never downsize on CPU alone — memory is buffer cache), batch (Spot
   candidate), cache (memory IS data).
8. **Savings Plans impact** — right-size at the effective (discounted)
   rate, not on-demand. Cross-family migration may orphan commitments.
9. **Spot evaluation** — for fault-tolerant workloads, Spot delivers
   60-90% savings vs on-demand.
10. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
    recommendation) or OPTIMIZED (all dimensions pass).

Emits a deterministic right-sizing block per instance:

```text
TARGET: <instance-id> (<instance-type>)
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <instance-type>, <architecture>, <pricing-model>, <region>
  Proposed: <instance-type>, <architecture>, <pricing-model>, <region>
  Dimensions changed: <idle | cpu-mem | family | graviton | burstable | workload | pricing | spot>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste an EC2 instance's utilization data and ask any of:

- "right-size this EC2 instance"
- "should I migrate to Graviton?"
- "is this Compute Optimizer finding actionable?"
- "is my t3.large running out of CPU credits?"
- "EC2 fleet right-sizing review"
- "should I use Spot for this workload?"
- "can I downsize this database?"

A bare instance ID + any optimization verb ("optimize this instance",
"cost review") also routes here via the orchestrator.

## Inputs

- Instance metadata: instance ID, current type, architecture, region,
  current pricing model (On-Demand / RI / Savings Plan / Spot).
- Utilization metrics (last 14-30 days):
  - `CPUUtilization` (CloudWatch AWS/EC2 namespace, always available)
  - `MemoryUtilization` / `mem_used_percent` (CloudWatch CWAgent
    namespace, REQUIRED for downsize recommendations)
  - `NetworkIn`, `NetworkOut` (CloudWatch, always available)
  - `DiskReadOps`, `DiskWriteOps` (CloudWatch, for instance-store
    workloads)
  - `CPUCreditBalance` (for t-family instances)
- Optional: Compute Optimizer EC2 finding document (finding,
  findingReasons, utilizationMetrics, recommendationOptions).
- Optional: termination protection status (`disableApiTermination`).
- Optional: workload context (web server, database, batch, cache, CI)
  for workload-specific sizing rules.
- Optional: active Savings Plans / RIs (for commitment-aware savings
  math).
- Optional: Docker image architecture (for Graviton compatibility).

## Outputs

- One right-sizing block per instance.
- Confidence level with rationale (HIGH requires CWAgent memory +
  Compute Optimizer cross-check + 14+ day window + clear thresholds).
- Estimated monthly and annual savings, broken down by dimension.
- Specific migration steps with CLI commands (stop-instances,
  modify-instance-attribute, start-instances, run-instances for
  Graviton, modify-instance-credit-specification for t-family).
- Termination protection check before any stop/terminate.
- Rollback path (original instance type) for production right-sizes.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Optimize specialist for EC2 compute cost).
- `/aws:audit-compute-optimizer-findings` to audit the confidence of a
  specific Compute Optimizer finding before acting on it.
- `/aws:optimize-ec2-reserved-capacity` for Reserved Instance and
  Savings Plan purchasing decisions (pricing model, not right-sizing).
- `/aws:optimize-ebs-volume` for EBS volume cost optimization (storage
  rather than compute).
