# Eval prompt: gp2-to-gp3-migration

Optimise the following EBS volume for cost. Walk the volume type migration
decision matrix and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

VolumeId: vol-gp2-to-gp3-migration
VolumeType: gp2
Size: 500 GB
Region: us-east-1
IOPS: 1500 (baseline for gp2 at this size)
Throughput: N/A (gp2)
Attached instance: i-prod-db-01 (m5.2xlarge, PostgreSQL primary)

Metrics (last 30 days):
  - VolumeReadOps + VolumeWriteOps: avg 250/s, max 400/s
  - VolumeQueueLength: avg 0.2, max 0.8
  - VolumeReadBytes + VolumeWriteBytes: avg 8 MB/s, max 15 MB/s
  - BurstBalance: avg 15%, min 0% (chronically depleted during peak
    hours — performance throttling observed)

Snapshot policy: no DLM or AWS Backup configured
FSR: not enabled

Workload context: PostgreSQL primary database on an m5.2xlarge. Burst
credit exhaustion causing intermittent I/O throttle during peak hours.
gp3 baseline 3000 IOPS would resolve this.
