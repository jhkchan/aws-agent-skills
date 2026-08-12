# Eval prompt: memory-missing-blocked

Right-size the following EC2 instance for cost. Walk the utilization-
driven decision matrix and emit the standard right-sizing block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

InstanceId: i-memory-missing-blocked
InstanceType: m5.xlarge
Architecture: x86_64
Region: us-east-1
Pricing: On-Demand
TerminationProtection: false

Metrics (last 14 days):
  - CPUUtilization avg: 8%, p95: 22%
  - MemoryUtilization: NOT AVAILABLE (CWAgent not installed)
  - NetworkIn avg: 15 MB/h
  - DiskReadOps avg: 80/s

Compute Optimizer finding: Overprovisioned (based on CPU only)
Note: Compute Optimizer does not have guest memory data either.

Workload context: Unknown application (no tags, no description).
Recently inherited from another team.
