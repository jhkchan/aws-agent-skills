# Fargate Cost Optimizer — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Mindset (moved from SKILL.md)

**One-line takeaway:** Fargate charges per vCPU-second and per
GB-second. Every dimension of optimization either reduces vCPU-seconds
(fewer vCPUs, cheaper ARM64 vCPUs, Spot pricing) or reduces GB-seconds
(less memory), or eliminates idle capacity (bin-packing, capacity
providers, Savings Plans). Start with right-sizing, then pricing model,
then architecture.

Three facts make Fargate cost optimization different from generic
container tuning:

- **Fargate task CPU and memory must be from a fixed combination
  table — you cannot pick arbitrary values.** There are 28 allowed
  combinations (e.g. 0.25 vCPU pairs with 0.5/1/2 GB; 1 vCPU pairs with
  2-8 GB). Right-sizing means finding the smallest combo that still
  meets the workload's needs, not arbitrary increments.
- **CloudWatch CPUUtilization and MemoryUtilization are measured
  against the task's configured limits, not the node.** A task at 15%
  CPUUtilization on a 2-vCPU config is using 0.3 vCPU — it can likely
  drop to 0.5 vCPU. The metric IS the right-sizing signal.
- **Fargate Spot and Savings Plans stack with architecture savings.**
  ARM64 is 20% cheaper per-unit. Spot is up to 70% cheaper. Savings
  Plans commits for 1-3 years at a discount. The optimal workload uses
  all three: ARM64 + Spot + Savings Plans for fault-tolerant, steady
  workloads; ARM64 + On-Demand for stateful services.

## Expert heuristic — right-size, pricing model, commitment (moved from SKILL.md)

Three rules, in order, produce 90% of Fargate savings:

1. **Right-size the task definition first.** This reduces the base cost
   that all other optimizations multiply against. A 2-vCPU task at 18%
   CPU is paying for 1.6 vCPUs it never uses. Dropping to 1 vCPU nearly
   halves the cost — and then Spot, ARM64, and Savings Plans all apply
   to the smaller (cheaper) base.
2. **Switch the pricing model second.** Once the task is right-sized,
   evaluate Spot for fault-tolerant workloads (70% off) and ARM64 for
   compatible runtimes (20% off). These are multiplicative: ARM64 Spot
   is 76% off the x86_64 On-Demand price of the same task.
3. **Commit with Savings Plans third.** Only after the task is
   right-sized and on the right pricing model. The SP commitment should
   match the steady-state baseline of the optimized configuration.
   Committing to an over-provisioned baseline locks in waste.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Fargate with EFA (Elastic Fabric Adapter, 2024-2025):** Fargate
  now supports EFA for HPC and distributed ML training workloads.
  EFA provides low-latency node-to-node communication. Relevant for
  distributed training (PyTorch DDP, TensorFlow) and MPI-based HPC.
  Not a cost optimization per se, but enables Fargate for workloads
  that previously required EC2 with EFA.
- **Fargate with instance storage (2025-2026):** Fargate tasks can now
  access ephemeral instance storage (NVMe-backed) for high-I/O
  workloads. This eliminates the need for EBS-attached storage for
  scratch space, reducing cost for tasks that need fast local disk
  (e.g., video transcoding, data processing intermediates).
- **Graviton3 on Fargate (2024+):** Fargate ARM64 tasks run on
  Graviton3 processors, which offer ~25% better price-performance
  than Graviton2. No configuration change needed — selecting ARM64
  automatically uses the latest Graviton generation.
- **Fargate Spot capacity provider improvements (2024-2025):** The
  FargateSpot capacity provider now supports `base` tasks on
  On-Demand, making it easier to maintain a minimum guaranteed
  capacity while running the bulk on Spot.
- **Compute Savings Plans coverage for Fargate (2024-2026):** Compute
  Savings Plans (1yr/3yr) apply to Fargate vCPU and GB charges,
  stacking with Spot and ARM64 for maximum savings.
