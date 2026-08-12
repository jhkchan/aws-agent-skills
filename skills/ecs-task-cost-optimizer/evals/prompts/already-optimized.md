# Eval prompt: already-optimized

Optimise the following ECS service for cost. Walk all optimization
dimensions (launch-type, architecture, right-size, spot, savings-plan,
placement, autoscaling) and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

ServiceName: svc-already-optimized
Cluster: prod-cluster
LaunchType: FARGATE
TaskDefinition: payment-api:50
CPU: 512 (0.5 vCPU)
Memory: 1024 MB
Architecture: arm64
Region: us-east-1
DesiredCount: 6
Capacity provider: FARGATE_SPOT (70% spot base + 30% on-demand top)

Metrics (last 30 days, Container Insights):
  - CPUUtilization avg: 28%, p95: 42%
  - MemoryUtilization avg: 40%, p95: 55%
  - RunningTaskCount avg: 6

Savings Plan coverage:
  - 1-year Compute SP covering $200/month ECS spend
  - Discount: 52% (blended Fargate rate after SP)
  - Utilization: 98% (fully utilized)

Workload context: payment processing API. Stateless, horizontally
scalable. Already on arm64 (Node.js 20). Already right-sized. Capacity
provider strategy: Fargate Spot 70% base + on-demand 30%. Auto-scaling:
target tracking at 60% CPUUtilization. Well-managed service — all
optimization dimensions addressed.

Cost Explorer (last month):
  - Fargate compute (pre-SP): $104.33
  - SP discount: -$54.25
  - Net compute: $50.08/month
