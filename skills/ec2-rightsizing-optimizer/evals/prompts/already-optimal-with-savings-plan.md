# Eval prompt: already-optimal-with-savings-plan

Optimize the EC2 instance configuration for cost. Walk the rightsizing
decision matrix and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

InstanceId: i-already-optimal-with-savings-plan
Current instance type: c6i.4xlarge
Region: us-east-1
Pricing: 3-year Compute Savings Plan covering 100% of hourly spend

Utilization metrics (last 30 days, CWAgent reporting):
  - CPUUtilization: avg=55%, max=70% (CloudWatch)
  - MemoryUtilization: avg=65%, max=78% (CloudWatchAgent)
  - NetworkIn: avg=2 MB/s, max=4 MB/s
  - DiskReadOps+DiskWriteOps: avg=100/s, max=150/s

Compute Optimizer finding: Optimized
Finding reasons: []

Workload context: C++ batch processing application using AVX2 SIMD
intrinsics for video transcoding. No arm64 build available (SIMD
intrinsics are x86-specific).
