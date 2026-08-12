# Eval prompt: fargate-to-ec2-crossover

Optimise the following ECS service for cost. Walk the Fargate vs EC2
launch type crossover decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

ServiceName: svc-fargate-to-ec2-crossover
Cluster: prod-cluster
LaunchType: FARGATE
TaskDefinition: web-api:15
CPU: 1024 (1 vCPU)
Memory: 2048 MB
Architecture: x86_64
Region: us-east-1
DesiredCount: 20
Capacity provider: FARGATE (on-demand)

Metrics (last 30 days, Container Insights):
  - CPUUtilization avg: 65%, p95: 78%
  - MemoryUtilization avg: 58%, p95: 70%
  - RunningTaskCount avg: 20

Workload context: customer-facing web API. Always-on 24/7 with steady
traffic. Team manages EC2 ASGs and is willing to adopt capacity
providers. No spot compatibility (stateful session cache per task —
cannot tolerate interruption).

Cost Explorer (last month):
  - Fargate compute: $720.80/month (20 tasks × $0.04937/hr × 730 hr)
  - No Savings Plan coverage.
