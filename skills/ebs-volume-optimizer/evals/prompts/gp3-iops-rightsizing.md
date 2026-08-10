# Eval prompt: gp3-iops-rightsizing

Optimise the following EBS volume for cost. Walk the IOPS/throughput right-
sizing decision matrix and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

VolumeId: vol-gp3-iops-rightsizing
VolumeType: gp3
Size: 800 GB
Region: us-east-1
IOPS: 8000 (provisioned — above 3000 baseline)
Throughput: 125 MB/s (baseline)
Attached instance: i-cache-server-01 (r6i.large)

Metrics (last 30 days):
  - VolumeConsumedReadWriteOps: avg 1500/s, max 2200/s
  - VolumeQueueLength: avg 0.05, max 0.2
  - VolumeReadBytes + VolumeWriteBytes: avg 10 MB/s, max 18 MB/s

Snapshot policy: DLM with 14-day retention (snapshots governed)
FSR: not enabled

Workload context: Redis cache server data volume. I/O is modest and well
below the 8000 provisioned IOPS. gp3 baseline 3000 IOPS provides 1.36x
headroom over the max consumed (2200). Throughput is at baseline (no
extra throughput cost).
