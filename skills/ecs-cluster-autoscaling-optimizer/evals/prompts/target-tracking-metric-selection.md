# Eval prompt: target-tracking-metric-selection

Optimise the following ECS cluster's autoscaling configuration for
workload-appropriate scaling. Walk the decision framework and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_IMPACT, MIGRATION_STEPS).

ClusterName: ecs-target-tracking-metric-selection
Launch type: EC2 (1 capacity provider: on-demand)
Capacity provider strategy: on-demand weight=1, base=2
Managed scaling: enabled
Placement strategy: binpack by memory + spread by az
Scale-in cooldown: 120 s
Target tracking: ECSServiceAverageCPUUtilization = 60%

Metrics (last 30 days):
  - CPUUtilization avg: 35%, p95: 48%
  - MemoryUtilization avg: 78%, p95: 92%
  - RunningEC2Tasks avg: 30, DesiredTasks avg: 30
  - OOMKilled task count: 145 in last 7 days (memory pressure)
  - Container instances: 12 total, 0 empty
  - CapacityProviderReservation avg: 70%

EC2 instances: m5.xlarge, 12 instances (4 vCPU, 16 GB each)
Services: 2 (Java Spring Boot JVM services with 8 GB heap each)

Workload context: Java Spring Boot services with large JVM heaps.
Each task allocates 8 GB heap. CPU is low (I/O-bound API) but
memory is the bottleneck. CPU-only scaling never triggers scale-out
even when memory is at 92%. OOM kills occurring daily.
