# Eval prompt: idle-downsize

Right-size the following EC2 instance for cost. Walk the utilization-
driven decision matrix and emit the standard right-sizing block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

InstanceId: i-idle-downsize
InstanceType: m5.2xlarge
Architecture: x86_64
Region: us-east-1
Pricing: On-Demand (no Savings Plan coverage)
TerminationProtection: false

Metrics (last 14 days):
  - CPUUtilization avg: 3.2%, p95: 7.1%
  - MemoryUtilization avg: 28% (CWAgent mem_used_percent)
  - NetworkIn avg: 12 MB/h
  - NetworkOut avg: 8 MB/h
  - DiskReadOps avg: 150/s
  - DiskWriteOps avg: 45/s

Compute Optimizer finding: Overprovisioned
Recommendation options:
  - rank: 1, instanceType: m5.large, performanceRisk: 1
  - rank: 2, instanceType: m5.xlarge, performanceRisk: 1

Workload context: Nginx web server serving static content and
reverse-proxying to an API. Stateless. 2 vCPU minimum for HA.
