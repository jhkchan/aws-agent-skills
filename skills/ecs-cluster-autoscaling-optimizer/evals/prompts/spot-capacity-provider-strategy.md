# Eval prompt: spot-capacity-provider-strategy

Optimise the following ECS cluster's autoscaling configuration for
cost. Walk the capacity provider decision framework and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_IMPACT, MIGRATION_STEPS).

ClusterName: ecs-spot-capacity-provider-strategy
Launch type: EC2 (1 capacity provider: on-demand)
Capacity provider strategy: on-demand weight=1, base=1
Managed scaling: enabled
Placement strategy: binpack by memory + spread by az
Scale-in cooldown: 120 s
Target tracking: ECSServiceAverageCPUUtilization = 65%

Metrics (last 30 days):
  - CPUUtilization avg: 35%, p95: 50%
  - MemoryUtilization avg: 42%, p95: 60%
  - RunningEC2Tasks avg: 25, DesiredTasks avg: 25
  - Container instances: 10 total, 1 with runningTasksCount=0
  - CapacityProviderReservation avg: 55%

EC2 instances: m5.xlarge, 10 instances
Services: 4 (stateless API services, horizontally scalable)

Workload context: stateless REST API services behind ALB.
No databases, no caches, no long-lived connections. Tasks
complete in < 500 ms average. Burst-tolerant for spot.
