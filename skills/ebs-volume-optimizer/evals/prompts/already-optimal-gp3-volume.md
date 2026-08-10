# Eval prompt: already-optimal-gp3-volume

Optimise the following EBS volume for cost. Walk all optimization dimensions
(type, capacity, IOPS, throughput, snapshot governance, FSR) and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

VolumeId: vol-already-optimal-gp3-volume
VolumeType: gp3
Size: 200 GB
Region: us-east-1
IOPS: 3000 (baseline)
Throughput: 125 MB/s (baseline)
Attached instance: i-web-server-01 (t3.medium)

Metrics (last 30 days):
  - VolumeReadOps + VolumeWriteOps: avg 120/s, max 200/s
  - VolumeQueueLength: avg 0.02, max 0.1
  - Actual data on volume: 170 GB (85% utilization)

Snapshot inventory:
  - Total snapshots: 7 (daily DLM policy, 7-day retention)
  - Total snapshot storage: ~1,400 GB (7 x 200 GB incremental)
  - DLM policy: ENABLED, 7-day daily retention

FSR: not enabled

Workload context: web server root volume. Volume type is gp3 (optimal).
IOPS and throughput are at baseline (no extra cost). Size is well-matched
to actual data. Snapshots are governed.
