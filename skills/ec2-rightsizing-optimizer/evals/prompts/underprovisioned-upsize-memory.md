# Eval prompt: underprovisioned-upsize-memory

Optimize the EC2 instance configuration for cost and performance. Walk
the rightsizing decision matrix and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

InstanceId: i-underprovisioned-upsize-memory
Current instance type: m5.xlarge
Region: us-east-1
Pricing: On-Demand

Utilization metrics (last 30 days, CWAgent reporting):
  - CPUUtilization: avg=75%, max=92% (CloudWatch)
  - MemoryUtilization: avg=88%, max=95% (CloudWatchAgent)
  - NetworkIn: avg=0.5 MB/s, max=1.0 MB/s
  - DiskReadOps+DiskWriteOps: avg=500/s, max=800/s

Compute Optimizer finding: Underprovisioned
Finding reasons: ["CPUUnderprovisioned", "MemoryUnderprovisioned"]
Recommendation options:
  - rank: 1, instanceType: r6i.2xlarge, performanceRisk: 1

Workload context: self-managed PostgreSQL on EC2; high read/write IOPS;
memory pressure visible in OOM kills (recent event in CloudWatch).
P99 query latency has degraded 3x in the last week.
