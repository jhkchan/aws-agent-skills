# Eval prompt: binpack-placement-efficiency

Optimise the following ECS cluster's autoscaling and placement for host
utilization. Walk the decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_IMPACT, MIGRATION_STEPS).

ClusterName: ecs-binpack-placement-efficiency
Launch type: EC2 (1 capacity provider: on-demand)
Capacity provider strategy: on-demand weight=1, base=1
Managed scaling: enabled
Placement strategy: spread by host
Scale-in cooldown: 120 s
Target tracking: ECSServiceAverageCPUUtilization = 60%

Metrics (last 30 days):
  - CPUUtilization avg: 30%, p95: 45%
  - MemoryUtilization avg: 25%, p95: 38%
  - RunningEC2Tasks avg: 15 (1 per host), DesiredTasks avg: 15
  - Container instances: 15 total, 6 with runningTasksCount=0 (40% empty)
  - CapacityProviderReservation avg: 65%

EC2 instances: m5.2xlarge, 15 instances (8 vCPU, 32 GB each)
Services: 3 (worker processes, each task uses 1 vCPU + 4 GB)

Workload context: batch worker cluster. Each worker task uses
1 vCPU and 4 GB memory. With spread-by-host, only 1 task runs
per 8-vCPU/32-GB host. 7 vCPUs and 28 GB wasted per host.
