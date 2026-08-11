# Eval prompt: rightsizing-overprovisioned-cpu-memory

Optimise the following Fargate task definition for cost. Walk all
optimization dimensions (right-size, Spot, ARM64, scheduling, savings
plans) and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

## Scenario

An ECS service on Fargate runs task definition `order-processor:42`.

## Known facts

- Task definition: `order-processor:42`
  - CPU: `2048` (2 vCPU)
  - Memory: `4096` (4 GB)
  - Architecture: `x86_64`
  - Container: Java 21 (Corretto), no `-Xmx` flag set
- Service: 10 desired tasks, running 24/7
- 14-day CloudWatch metrics:
  - CPUUtilization: average 18%, maximum 35%
  - MemoryUtilization: average 42%, maximum 55%
- No Fargate Spot, no Savings Plans in use
- Cost Explorer: $636/month for this service (Fargate On-Demand)

## Symptom

The service is functional but the Fargate bill is higher than expected.
The team wants to reduce cost without affecting performance.
