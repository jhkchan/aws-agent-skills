# Advanced Patterns (load on demand) — ECS Fargate Deployer

Latest-feature notes moved verbatim from SKILL.md. Loaded on demand.

---

## Latest ECS Fargate features (2024-2026) (moved from SKILL.md)

- **Fargate Spot capacity provider (GA):** Spot drains tasks on 2-minute
  warning. Use capacity-provider strategy with `base=N` on FARGATE plus
  FARGATE_SPOT for burst capacity.
- **EFA support on Fargate (2024-2025):** Elastic Fabric Adapter for ML/HPC
  workloads. Available on selected CPU configs.
- **Container health check improvements (2024-2025):** `START_PERIOD`
  (1-300s) configurable per container. Eliminates false-negative rollbacks
  for slow-start JVM/Spring workloads.
- **Availability Zone rebalancing (2024-2025):** ECS auto-rebalances tasks
  across AZs after failure. Set `availabilityZoneRebalancing=ENABLED`.
- **Deployment circuit breaker rollback (GA):** auto-rolls back failed
  deployments. Requires `enableExecution=true` + container health check.
- **Graviton (ARM64) on Fargate (2024-2025):** `runtimePlatform.cpuArchitecture=ARM64`
  for up to 20% price-performance. Image must be ARM64.
- **Fargate platform version 1.4 (current default):** `LATEST` no longer
  auto-upgrades — pin `platformVersion` for reproducibility.
- **ECS Exec (session manager):** `enableExecuteCommand` for shell access.
  Never enable in production without audit review.
