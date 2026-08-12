# Eval prompt: already-optimal-autoscaling

Optimise the following ECS cluster's autoscaling configuration. Walk all
optimization dimensions (capacity provider strategy, managed scaling,
target tracking, scale-in cooldown, bin-packing, Fargate, warm-up,
drain lifecycle, desired/running gap, placement strategy, scaling mode)
and emit the standard optimization block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_IMPACT, MIGRATION_STEPS).

ClusterName: ecs-already-optimal-autoscaling
Launch type: EC2 (2 capacity providers: on-demand, spot)
Capacity provider strategy: on-demand weight=1, base=2; spot weight=4, base=0
Managed scaling: enabled (targetCapacity=100)
Placement strategy: binpack by memory + spread by az
Scale-in cooldown: 120 s
Target tracking: ECSServiceAverageCPUUtilization = 65% (CPU-bound workload)

Metrics (last 30 days):
  - CPUUtilization avg: 62%, p95: 70%
  - MemoryUtilization avg: 55%, p95: 65%
  - RunningEC2Tasks avg: 28, DesiredTasks avg: 28
  - Container instances: 8 total, 0 empty
  - CapacityProviderReservation avg: 95%
  - Spot instance interruptions: 3 in last 30 days (handled gracefully)

EC2 instances: m5.xlarge, 6 on-demand + 2 spot
Services: 3 (stateless microservices, CPU-bound, burst-tolerant)

Workload context: well-managed production cluster. Managed scaling
active, spot capacity provider with on-demand base, binpack for
density + AZ spread for availability. Cooldown tuned for spiky
traffic. No optimization dimension has positive improvement.
