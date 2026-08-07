# Eval prompt: memory-data-missing-blocked

Optimize the EC2 instance configuration for cost. Walk the rightsizing
decision matrix and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

InstanceId: i-memory-data-missing-blocked
Current instance type: m5.xlarge
Region: us-east-1
Pricing: On-Demand

Utilization metrics (last 30 days):
  - CPUUtilization: avg=12%, max=20% (CloudWatch)
  - MemoryUtilization: ABSENT (CloudWatch Agent not installed)
  - NetworkIn: avg=0.1 MB/s, max=0.2 MB/s

Compute Optimizer finding: Overprovisioned (LOW confidence — memory
inferred from instance type specifications, performanceRisk 4)

Workload context: unknown runtime; metrics show low CPU but no memory
visibility. The application team is uncertain whether the workload is
memory-bound.
