# Eval prompt: capacity-provider-spot

Optimise the following ECS service for cost. Walk the capacity provider
strategy (spot vs on-demand) decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

ServiceName: svc-capacity-provider-spot
Cluster: prod-cluster
LaunchType: EC2
TaskDefinition: frontend-web:30
CPU: 512 (0.5 vCPU)
Memory: 1024 MB
Architecture: x86_64
Region: us-east-1
DesiredCount: 12
Capacity provider: on-demand-cap-provider (100% on-demand)

Metrics (last 30 days, Container Insights):
  - CPUUtilization avg: 45%, p95: 60%
  - MemoryUtilization avg: 50%, p95: 65%
  - RunningTaskCount avg: 12

Cluster details:
  - EC2 instances: 4x m5.large (2 vCPU, 8 GB each)
  - Average instance utilization: 55% CPU, 50% memory
  - Placement strategy: spread (default)

Workload context: stateless React SSR web frontend. No session state
(using Redis ElastiCache for sessions). Can tolerate spot interruption
with graceful shutdown (SIGTERM handler, 30s stopTimeout). Traffic is
bursty but fault-tolerant behind ALB.

Cost Explorer (last month):
  - EC2 compute: $280.32/month (4 × $0.096 × 730)
  - No Savings Plan coverage.
