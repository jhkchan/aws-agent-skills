# Eval prompt: overprovisioned-downsize-graviton

Optimize the EC2 instance configuration for cost. Walk the rightsizing
decision matrix and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

InstanceId: i-overprovisioned-downsize-graviton
Current instance type: m5.2xlarge
Region: us-east-1
Pricing: On-Demand (no RI/Savings Plan)

Utilization metrics (last 30 days, CWAgent reporting):
  - CPUUtilization: avg=8%, max=15% (CloudWatch)
  - MemoryUtilization: avg=22%, max=30% (CloudWatchAgent)
  - NetworkIn: avg=0.05 MB/s, max=0.1 MB/s
  - DiskReadOps+DiskWriteOps: avg=10/s, max=20/s

Compute Optimizer finding: Overprovisioned
Finding reasons: ["CPUOverprovisioned", "MemoryOverprovisioned"]
Recommendation options:
  - rank: 1, instanceType: t3.large, performanceRisk: 1,
    savingsOpportunity: {savingsPercentage: 75, estimatedMonthlySavings: 150}
Last refresh: 2026-07-25

Workload context: Java 17 application (Spring Boot), containerized via
Docker multi-arch image (arm64 available), steady-state 24/7. Small
memory footprint; mostly idle between batch jobs.
