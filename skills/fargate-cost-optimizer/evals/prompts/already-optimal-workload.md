# Eval prompt: already-optimal-workload

Optimise the following Fargate workload for cost. Walk all optimization
dimensions and emit the standard optimization block (TARGET, VERDICT,
REASON).

## Scenario

An ECS service has already been optimized across all dimensions. The
team wants to verify there are no further savings opportunities.

## Known facts

- Task definition: `web-frontend:30`
  - CPU: `512` (0.5 vCPU)
  - Memory: `1024` (1 GB)
  - Architecture: `ARM64` (Graviton)
- Service: capacity provider strategy:
  - FargateSpot: weight 4, base 0
  - Fargate (On-Demand): weight 1, base 1
  - Current: 1 On-Demand base task + 7 Spot tasks = 8 total
- Application Auto Scaling enabled:
  - Target: 60% CPUUtilization
  - Min capacity: 2, Max capacity: 20
  - ScaleInCooldown: 300s, ScaleOutCooldown: 60s
- 1-year Compute Savings Plan covers the steady-state baseline
- 14-day CloudWatch metrics:
  - CPUUtilization: average 58%, maximum 75%
  - MemoryUtilization: average 65%, maximum 72%

## Symptom

The team is doing a FinOps review and wants to confirm this service
has no further optimization opportunities.
