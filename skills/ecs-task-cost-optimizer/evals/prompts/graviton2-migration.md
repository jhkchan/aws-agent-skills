# Eval prompt: graviton2-migration

Optimise the following ECS service for cost. Walk the Graviton2 (arm64)
architecture migration decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

ServiceName: svc-graviton2-migration
Cluster: prod-cluster
LaunchType: FARGATE
TaskDefinition: order-api:42
CPU: 512 (0.5 vCPU)
Memory: 1024 MB
Architecture: x86_64
Region: us-east-1
DesiredCount: 8
Capacity provider: FARGATE (on-demand)

Metrics (last 30 days, Container Insights):
  - CPUUtilization avg: 35%, p95: 52%
  - MemoryUtilization avg: 40%, p95: 55%
  - RunningTaskCount avg: 8

Workload context: Node.js 20 REST API. Pure JavaScript with no native
C/C++ dependencies (no node-gyp, no ffi-napi). Container image uses
node:20-alpine base. All npm packages are pure JS.

Cost Explorer (last month):
  - Fargate compute: $144.44/month (8 × 0.5 × $0.04048 × 730 + 8 × 1.0 × $0.004445 × 730)
