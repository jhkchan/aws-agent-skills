# Eval prompt: savings-plans-steady-state

Optimise the following Fargate workload for cost. Walk all optimization
dimensions and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

## Scenario

An ECS service runs a long-running reporting daemon on Fargate
On-Demand. The workload is steady-state but cannot tolerate
interruption.

## Known facts

- Task definition: `reporter:5`
  - CPU: `1024` (1 vCPU)
  - Memory: `2048` (2 GB)
  - Architecture: `x86_64`
- Service: 8 desired tasks, running 24/7, 365 days/year
- All tasks on Fargate On-Demand (no Spot, no Savings Plans)
- The workload CANNOT tolerate interruption: each task generates
  long-running reports (30-90 minutes each). Spot reclamation would
  lose in-progress work.
- 14-day CloudWatch metrics:
  - CPUUtilization: average 60%, maximum 75%
  - MemoryUtilization: average 55%, maximum 68%
- Cost Explorer: $252/month (8 tasks x $31.57/task/month)

## Symptom

The team wants to reduce the monthly Fargate bill. The workload must
stay On-Demand (no Spot) because report generation cannot be
interrupted. CPU and memory are well-utilized (no right-sizing
opportunity).
