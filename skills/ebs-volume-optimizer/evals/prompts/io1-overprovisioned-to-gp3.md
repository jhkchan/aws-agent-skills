# Eval prompt: io1-overprovisioned-to-gp3

Optimise the following EBS volume for cost. Walk the volume type migration
and IOPS right-sizing decision matrix and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

VolumeId: vol-io1-overprovisioned-to-gp3
VolumeType: io1
Size: 1000 GB
Region: us-east-1
IOPS: 10000 (provisioned)
Attached instance: i-app-server-02 (m5.xlarge)

Metrics (last 30 days):
  - VolumeConsumedReadWriteOps: avg 1200/s, max 1800/s
  - VolumeQueueLength: avg 0.1, max 0.3
  - VolumeReadBytes + VolumeWriteBytes: avg 12 MB/s, max 20 MB/s

Snapshot policy: DLM with 7-day retention (snapshots governed)
FSR: not enabled

Workload context: application server data volume. I/O is modest and well
below the 10000 provisioned IOPS. m5.xlarge is Nitro-based so gp3 is
fully supported.
