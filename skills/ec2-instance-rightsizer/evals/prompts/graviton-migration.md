# Eval prompt: graviton-migration

Right-size the following EC2 instance for cost. Walk the Graviton
(arm64) migration decision framework and emit the standard right-sizing
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

InstanceId: i-graviton-migration
InstanceType: m5.xlarge
Architecture: x86_64
Region: us-east-1
Pricing: On-Demand
TerminationProtection: false

Metrics (last 30 days):
  - CPUUtilization avg: 35%, p95: 62%
  - MemoryUtilization avg: 50% (CWAgent mem_used_percent)
  - NetworkIn avg: 85 MB/h
  - NetworkOut avg: 120 MB/h

Compute Optimizer finding: Optimized (right-sized)

Workload context: Python 3.12 + Node.js 20 API server. Dependencies:
requests, numpy (has aarch64 wheels), psycopg2-binary (has aarch64
wheels). No JNI. No C extensions beyond numpy. No Docker containers
(bare metal Python/Node). Graviton3 (m7g) is available in this AZ.
