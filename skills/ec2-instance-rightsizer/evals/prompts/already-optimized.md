# Eval prompt: already-optimized

Right-size the following EC2 instance for cost. Walk all right-sizing
dimensions (idle, cpu-mem, family, graviton, burstable, workload,
pricing, spot) and emit the standard right-sizing block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

InstanceId: i-already-optimized
InstanceType: r6i.2xlarge
Architecture: x86_64
Region: us-east-1
Pricing: On-Demand
TerminationProtection: true

Metrics (last 30 days):
  - CPUUtilization avg: 42%, p95: 65%
  - MemoryUtilization avg: 68% (CWAgent mem_used_percent)
  - NetworkIn avg: 200 MB/h
  - DiskReadOps avg: 2000/s
  - DiskWriteOps avg: 800/s

Compute Optimizer finding: Optimized

Workload context: PostgreSQL 16 production database. Uses PostGIS
extension compiled for x86_64 (no arm64 build available).
shared_buffers = 16 GB (25% of 64 GB RAM). Buffer cache hit ratio:
99.2%.
