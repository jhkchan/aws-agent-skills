# Eval prompt: graviton-arm64-migration

Optimise the following Fargate workload for cost. Walk all optimization
dimensions and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

## Scenario

An ECS service runs a Java 21 application on x86_64 Fargate. The team
wants to evaluate architecture migration and other cost savings.

## Known facts

- Task definition: `api-server:15`
  - CPU: `2048` (2 vCPU)
  - Memory: `4096` (4 GB)
  - Architecture: `x86_64`
  - Container: Java 21 (Amazon Corretto), `-XX:MaxRAMPercentage=75`
- Service: 15 desired tasks, running 24/7
- No Fargate Spot, no Savings Plans in use
- 14-day CloudWatch metrics:
  - CPUUtilization: average 55%, maximum 78%
  - MemoryUtilization: average 70%, maximum 82%
- Cost Explorer: $953/month (Fargate On-Demand, x86_64)
- The image is built with `docker build` and pushed to ECR. No native
  C libraries — pure Java application.

## Symptom

The team wants to reduce the monthly Fargate bill. CPU and memory
utilization are in the healthy range (right-sizing is not the primary
opportunity).
