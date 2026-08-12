# Eval prompt: managed-scaling-migration

Optimise the following ECS cluster's autoscaling configuration for
utilization and cost. Walk the capacity provider decision framework and
emit the standard optimization block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_IMPACT, MIGRATION_STEPS).

ClusterName: ecs-managed-scaling-migration
Launch type: EC2 (1 capacity provider: on-demand)
Capacity provider strategy: on-demand weight=1, base=0
Managed scaling: disabled (using legacy cluster-autoscaler)
Placement strategy: spread by host
Scale-in cooldown: 300 s (default)
Target tracking: ECSServiceAverageCPUUtilization = 60%

Metrics (last 30 days):
  - CPUUtilization avg: 35%, p95: 55%
  - MemoryUtilization avg: 28%, p95: 45%
  - RunningEC2Tasks avg: 40, DesiredTasks avg: 40
  - Container instances: 20 total, 8 with runningTasksCount=0 (40% empty)
  - CapacityProviderReservation: not configured (managed scaling off)

EC2 instances: m5.2xlarge, 20 instances, avg age 45 days
Services: 6 (all stateless microservices, burst-tolerant)

Workload context: stateless microservices (API, worker, scheduler).
No stateful workloads. Traffic is bursty during business hours.
Legacy cluster-autoscaler has known scale-out lag of 3-5 minutes.
