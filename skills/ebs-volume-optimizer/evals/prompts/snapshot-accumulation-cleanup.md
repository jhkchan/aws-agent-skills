# Eval prompt: snapshot-accumulation-cleanup

Optimise the following EBS volume for cost. Walk all optimization dimensions
(type, capacity, IOPS, throughput, snapshot governance, FSR) and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

VolumeId: vol-snapshot-accumulation-cleanup
VolumeType: gp3
Size: 500 GB
Region: us-east-1
IOPS: 3000 (baseline, free)
Throughput: 125 MB/s (baseline, free)
Attached instance: i-analytics-01 (r5.large)

Metrics (last 30 days):
  - VolumeReadOps + VolumeWriteOps: avg 180/s, max 300/s
  - VolumeQueueLength: avg 0.05, max 0.2
  - BurstBalance: N/A (gp3 has no burst credits)

Snapshot inventory:
  - Total snapshots: 145
  - Average snapshot size: 500 GB
  - Total snapshot storage: ~72,500 GB
  - No DLM or AWS Backup policy
  - 90 snapshots older than 90 days (0 restores in 90 days)
  - 55 snapshots from the last 90 days

FSR: not enabled

Workload context: analytics data volume. Volume type is already gp3
(optimal). The cost waste is entirely in snapshot accumulation.
