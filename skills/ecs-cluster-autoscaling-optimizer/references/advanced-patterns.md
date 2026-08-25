# Advanced Patterns (load on demand) — ECS Cluster Autoscaling Optimizer

Quick-start headline rules, mindset prose, Step 0 non-obvious behaviours, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Quick start — five headline rules (moved from SKILL.md)

- **Managed EC2 capacity provider auto-scaling replaces Cluster Autoscaler.**
  The legacy `cluster-autoscaler` project (or its K8s equivalent for
  ECS) is obsolete for native ECS. The managed capacity provider has
  built-in target tracking on `CapacityProviderReservation` and handles
  scale-out AND scale-in natively. Migrate if still on the legacy path.
- **Spot base + on-demand burst is the cost-optimal pattern.** Set
  `base = 2` on the on-demand provider (steady-state floor), `weight =
  1` on spot (fills burst capacity at 70% discount). This avoids
  spot-only risk while capturing the majority of the savings.
- **Binpack placement maximizes utilization.** The default `spread`
  strategy places one task per host, wasting 60-80% of host capacity.
  Switch to `binpack` (by `memory` or `cpu`) to pack tasks densely and
  reduce the host count.
- **Scale-in cooldown 300 s is too long for spiky workloads.** Default
  is 300 s; for microservices with bursty traffic, 60-120 s prevents
  stranded hosts from lingering after the burst ends.
- **Empty hosts are pure waste.** A container instance with 0 running
  tasks costs the full EC2 rate. Detect with
  `describe-container-instances` and eliminate via scale-in or binpack
  placement.

## Mindset — four guiding principles (moved from SKILL.md)

ECS cluster autoscaling optimization is a utilization-and-cost decision.
The goal is the capacity provider configuration and placement strategy
that maximizes host utilization (binpack) while preserving availability
(on-demand base for steady state + spot for burst) — not the absolute
minimum instances that run tasks.

Four principles guide every recommendation:

- **Managed scaling adapts; Cluster Autoscaler does not.** The managed
  capacity provider observes `CapacityProviderReservation` and scales
  natively. The legacy Cluster Autoscaler is a separate controller with
  known lag, race conditions, and extra operational overhead.
- **Spot base + on-demand burst is the cost-optimal hybrid.** Pure
  on-demand pays full price; pure spot risks availability. The `base`
  parameter on on-demand ensures a steady-state floor; spot `weight`
  captures burst capacity at a discount.
- **Binpack placement maximizes utilization.** The default `spread`
  strategy wastes host capacity by distributing tasks one-per-host.
  `binpack` packs tasks densely, reducing the total host count.
- **Scale-in cooldown controls cost during traffic dips.** A long
  cooldown (300 s default) keeps stranded hosts alive after a burst
  ends. A shorter cooldown (60-120 s) for microservices eliminates
  waste faster.

## Step 0: Non-obvious behaviours that change the recommendation (moved from SKILL.md)

- **`base` on a capacity provider is the steady-state floor.** Set `base`
  on the on-demand provider to guarantee a minimum number of tasks on
  on-demand regardless of spot availability.
- **`weight` controls the distribution ratio.** For every N tasks, the
  ratio is `weight`-proportional across providers. For cost-optimization:
  on-demand weight = 1, spot weight = 4 (with on-demand base = 2).
- **Managed scaling uses CapacityProviderReservation.** The managed
  capacity provider reports its own CloudWatch metric for target
  tracking, distinct from service-level ECSServiceAverageCPUUtilization.
- **Scale-in has two cooldowns: policy-level and capacity-provider-level.**
  The policy `CooldownSeconds` defaults to 300. The
  `instanceWarmupPeriod` controls how fast new instances register.
- **Spread strategy is the default but wastes hosts.** `spread` by
  `host` leaves 60-80% of host capacity unused. Switch to `binpack`.
- **Binpack by memory vs CPU depends on the bottleneck resource.**
  Memory-heavy (JVM, ML) → binpack by `memory`. CPU-heavy → by `cpu`.
- **Drain lifecycle: DRAINING to DEPROVISIONING.** When scale-in targets
  an instance, ECS moves it to `DRAINING`, reschedules tasks, then
  `DEPROVISIONING` terminates it. Takes 60-300 s depending on shutdown.
- **EC2 instance warm-up adds 60-120 seconds.** Boot, ECS agent
  registration, and health checks before tasks can be placed.
- **Fargate has no capacity provider to tune.** Tasks are serverless.
  Only optimization is CPU/memory right-sizing at the task level.
- **Spot instance interruption gives 2-minute warning.** Tasks must
  drain within that window or they are force-terminated.
- **Desired count != running count means tasks are failing to place.**
  Sustained gap = cluster lacks capacity. This is a scale-out signal.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Managed EC2 capacity provider auto-scaling (GA 2024):** Native ECS
  managed scaling on `CapacityProviderReservation`. Replaces the legacy
  Cluster Autoscaler for ECS.
- **Capacity provider weight and base refinement (2024-2025):** `base`
  on on-demand guarantees a minimum task floor; `weight` controls the
  distribution ratio across providers.
- **Fargate capacity up to 16 vCPU / 120 GB (2024):** Expanded task
  size limits for larger workloads.
- **ECS Service Connect (2024-2025):** Built-in service mesh for
  inter-task communication. Does not affect capacity provider tuning.
- **Bottlerocket AMI for ECS (2024):** Minimal boot time (15-30 s).
  Reduces `instanceWarmupPeriod` from 60 s to 30 s.
- **Spot instance interruption handler (2024-2025):** ECS drains tasks
  on spot instances receiving a 2-minute reclaim notice automatically.
- **CapacityProviderReservation CloudWatch metric (2024):** Direct
  visibility into managed scaling target capacity percentage.
- **Application Auto Scaling dual-policy (2025):** A service can now
  have both CPU and memory target-tracking policies simultaneously.
