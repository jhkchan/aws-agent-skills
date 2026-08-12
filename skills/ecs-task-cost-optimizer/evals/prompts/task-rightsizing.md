# Eval prompt: task-rightsizing

Optimise the following ECS service for cost. Walk the task definition
right-sizing decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

ServiceName: svc-task-rightsizing
Cluster: prod-cluster
LaunchType: FARGATE
TaskDefinition: data-processor:7
CPU: 1024 (1 vCPU)
Memory: 2048 MB
Architecture: x86_64
Region: us-east-1
DesiredCount: 8
Capacity provider: FARGATE (on-demand)

Metrics (last 30 days, Container Insights):
  - CPUUtilization avg: 12%, p95: 25%
  - MemoryUtilization avg: 18%, p95: 30%
  - RunningTaskCount avg: 8

Workload context: data enrichment service processing SQS messages.
Low CPU and memory utilization indicates over-provisioning. No native
dependencies (Python 3.12). No compliance or latency constraints that
require high headroom.

Cost Explorer (last month):
  - Fargate compute: $288.32/month
