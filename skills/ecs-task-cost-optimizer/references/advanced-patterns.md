# Advanced Patterns (load on demand) — ECS Task Cost Optimizer

Quick-start headline rules, mindset prose, Step 0 non-obvious billing behaviours, spot interruption handling, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Quick start — headline rules and cost formula (moved from SKILL.md)

- **Launch type is the #1 lever.** Fargate charges per-second (1-minute
  minimum); EC2 charges per-second (60-second minimum) but requires
  capacity management. For always-on workloads at >30% steady
  utilization, EC2 backing is cheaper. For bursty or <30% utilization,
  Fargate avoids paying for idle compute.
- **Cost formula — Fargate (memorise this):**
  `cost = (vCPU_hours × $0.04048) + (GB_hours × $0.004445)`
  Per-second after 1-minute minimum. vCPU and memory billed independently.
- **Cost formula — EC2-backed ECS:**
  `cost = EC2_instance_hourly (regardless of task count)`
  The ECS surcharge is $0; you pay for the EC2 instances in the cluster.
- **Graviton2 (arm64) is a free 20%.** arm64 task definitions cost ~20%
  less on both Fargate and EC2 (Graviton instances). Check application
  compatibility (compiled binaries, JNI, native libs) before migrating.
- **Spot capacity providers save 30-70%.** For fault-tolerant workloads,
  a spot base capacity provider with an on-demand top provider delivers
  the best cost profile. Never use spot for stateful single-instance
  services.

## Mindset — four guiding principles (moved from SKILL.md)

ECS cost optimization is a utilization-and-commitment exercise. The goal
is the launch type, architecture, task size, and capacity strategy that
minimizes dollar cost while preserving availability and latency SLOs.

Four principles guide every recommendation:

- **The Fargate-EC2 crossover is workload-specific.** Fargate's premium
  over EC2 is roughly 30-50% for always-on workloads. Below ~30%
  steady utilization, Fargate's per-second billing wins because you
  don't pay for idle hosts. Above ~30%, EC2's lower base rate wins.
- **Right-sizing compounds.** An over-provisioned task (1024 CPU at 10%
  utilization) on Fargate costs 4x what it should. On EC2, it wastes
  cluster capacity that could pack additional tasks. Either way, the
  cost leak is proportional to the over-allocation.
- **Commitment discounts stack on top of optimization.** A Compute
  Savings Plan applies to both Fargate and EC2-backed ECS. Apply it
  AFTER right-sizing and architecture migration — committing to
  over-provisioned spend locks in waste.
- **Spot is a strategy, not a setting.** Spot capacity requires
  divergence handling (connection draining, request hedging, graceful
  shutdown). A capacity provider strategy with spot base + on-demand
  top is the production-grade pattern.

## Step 0: Non-obvious behaviours that change the recommendation (moved from SKILL.md)

- **Fargate bills CPU and memory independently and per-second.** A task
  running for 90 seconds is billed for 90 seconds (1.5 minutes ×
  combined rate). The 1-minute minimum means tasks running < 60 seconds
  are billed for a full minute.
- **Fargate vCPU is not the same as EC2 vCPU.** Fargate tasks get
  dedicated vCPU; EC2-backed tasks share host vCPU via the Docker
  runtime. 1 Fargate vCPU performs similarly to 1 EC2 vCPU but the
  billing model is different (per-second vs per-hour).
- **Graviton2 (arm64) costs ~20% less on both Fargate and EC2.**
  Fargate arm64 pricing is lower per vCPU-hour and GB-hour. EC2
  Graviton instances (c7g, m7g, r7g) have lower hourly rates than x86
  equivalents. Check application compatibility before migrating.
- **Compute Savings Plans apply to BOTH Fargate and EC2-backed ECS.** A
  single Compute SP covers Fargate vCPU/GB-hours and EC2 instance-hours.
  This is unlike RIs which are instance-specific.
- **Spot capacity provider requires fault tolerance.** Spot instances
  can be reclaimed with 2-minute warning. Services must handle SIGTERM
  gracefully with on-demand fallback. Never use spot for stateful
  single-instance databases.
- **Task placement strategy affects EC2 density.** `binpack` fills
  instances before starting new ones (maximizes density). `spread`
  distributes across instances (maximizes availability). Default is
  `spread`.
- **Container Insights has a cost.** Container Insights charges $0.01
  per container instance per hour for the enhanced metrics. For large
  clusters, this adds up — but the optimization value typically exceeds
  the observability cost.
- **EFS charges per provisioned throughput, not per GB.** For ECS tasks
  using EFS for persistent storage, the cost model is throughput-based
  (provisioned or bursting). EBS charges per GB-month. Choose based on
  access pattern, not just capacity.
- **Standalone tasks are billed identically to service tasks.** A task
  definition deployed as a standalone task (one-shot batch job) costs
  the same per-second as a service task. The difference is lifecycle:
  services auto-restart; standalone tasks run once.
- **Daemon scheduling strategy deploys one task per instance.** This is
  useful for log agents (Firelens, CloudWatch agent) but means the task
  count scales with the instance count, not the application load.

## Step 4 — spot interruption handling (moved from SKILL.md)

**Spot interruption handling:**
ECS spot capacity providers integrate with EventBridge for 2-minute
reclaim warnings. Ensure:
- Task `stopTimeout` >= 30 seconds for graceful shutdown
- Application handles SIGTERM (flush buffers, close connections)
- Capacity provider strategy has on-demand fallback (base >= 2)

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **ECS Fargate arm64 (Graviton2) GA (2024):** Full support for arm64
  on Fargate. ~20% cheaper than x86_64.
- **Capacity provider managed scaling enhancements (2024-2025):**
  Tighter target-capacity tracking for EC2-backed clusters.
- **Container Insights enhanced metrics (2024):** Per-task CPU, memory,
  network, and storage metrics.
- **ECS Service Connect (2024 GA):** Built-in service discovery and
  load balancing without Cloud Map or ALB cost.
- **Fargate per-second billing (2024):** Consistent per-second billing
  across all regions with 1-minute minimum.
- **Graviton4 instances (2024-2025):** c8g, m8g, r8g with improved
  price-performance over Graviton3.
