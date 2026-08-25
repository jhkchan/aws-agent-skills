# Diagnostic Commands (load on demand) — EBS Volume Optimizer

Pre-flight and diagnostic command listings, moved verbatim from SKILL.md.


---

## Pre-flight: Required data sources (I/O metrics, snapshot inventory, FSR) (moved from SKILL.md)

```bash
# 1. Capture the volume configuration
aws ec2 describe-volumes --volume-ids <vol-id> --output json | \
  jq '.Volumes[] | {VolumeId, VolumeType, Size, Iops, Throughput,
    State, Attachments, AvailabilityZone, KmsKeyId}'

# 2. Pull 14-30 day I/O metrics
START=$(date -d '-30 days' +%FT%TZ)
END=$(date +%FT%TZ)

aws cloudwatch get-metric-statistics --namespace AWS/EBS \
  --metric-name VolumeReadOps \
  --dimensions Name=VolumeId,Value=<vol-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum,Sum \
  --output json > read-ops.json

aws cloudwatch get-metric-statistics --namespace AWS/EBS \
  --metric-name VolumeWriteOps \
  --dimensions Name=VolumeId,Value=<vol-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum,Sum \
  --output json > write-ops.json

aws cloudwatch get-metric-statistics --namespace AWS/EBS \
  --metric-name VolumeQueueLength \
  --dimensions Name=VolumeId,Value=<vol-id> \
  --start-time $START --end-time $END \
  --period 300 --statistics Average,Maximum \
  --output json > queue-length.json

# 3. For io1/io2 volumes — check consumed vs provisioned IOPS
aws cloudwatch get-metric-statistics --namespace AWS/EBS \
  --metric-name VolumeConsumedReadWriteOps \
  --dimensions Name=VolumeId,Value=<vol-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum \
  --output json > consumed-iops.json

# 4. For gp2 volumes — check burst credit balance
aws cloudwatch get-metric-statistics --namespace AWS/EBS \
  --metric-name BurstBalance \
  --dimensions Name=VolumeId,Value=<vol-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Minimum \
  --output json > burst-balance.json

# 5. Capture snapshot inventory for this volume
aws ec2 describe-snapshots --filters Name=volume-id,Values=<vol-id> \
  --output json | jq '.Snapshots | length, ([.[].VolumeSize] | add)'

# 6. Check for FSR (Fast Snapshot Restore) on snapshots
aws ec2 describe-fast-snapshot-restores --output json | \
  jq '.FastSnapshotRestores[] | select(.SnapshotId | contains("<snapshot-id>"))'
```

---

## Step 2: Identifying over-sized volumes (commands) (moved from SKILL.md)

#### Identifying over-sized volumes

```bash
# Check actual data on the volume (from the attached instance)
# Method 1: df on the instance (requires SSM or SSH)
aws ssm send-command --instance-id <instance-id> \
  --document-name "AWS-RunShellScript" \
  --parameters commands=["df -h /dev/xvdf", "df -BG /dev/xvdf | tail -1"] \
  --output json

# Method 2: Estimate from CloudWatch throughput
# If VolumeReadBytes + VolumeWriteBytes is consistently low AND the
# volume is large, it may be over-sized.
aws cloudwatch get-metric-statistics --namespace AWS/EBS \
  --metric-name VolumeReadBytes \
  --dimensions Name=VolumeId,Value=<vol-id> \
  --start-time $START --end-time $END \
  --period 86400 --statistics Sum \
  --output json | jq '.Datapoints | (map(.Sum) | add) as $total_read
    | {total_read_bytes_month: $total_read, total_read_gb_month: ($total_read / 1073741824)}'
```

---

## Step 4: Snapshot audit commands (moved from SKILL.md)

#### Snapshot audit

```bash
# Count snapshots and total size per volume
aws ec2 describe-snapshots --owner-ids self --output json | \
  jq '[.Snapshots[] | {SnapshotId, VolumeId, StartTime, VolumeSize}] as $snaps
    | ($snaps | length) as $count
    | (($snaps | map(.VolumeSize) | add) // 0) as $total_gb
    | {snapshot_count: $count, total_snapshot_size_gb: $total_gb}'

# Check for DLM (Data Lifecycle Manager) policies
aws dlm get-lifecycle-policies --output json | \
  jq '.Policies[] | {PolicyId, Description, State, PolicyType}'

# Check for AWS Backup plans governing EBS
aws backup list-backup-plans --output json | \
  jq '.BackupPlansList[]? | {BackupPlanId, BackupPlanName}'

# Check for FSR (Fast Snapshot Restore) — expensive
aws ec2 describe-fast-snapshot-restores --output json | \
  jq '.FastSnapshotRestores[]? | {SnapshotId, AvailabilityZone, State}'
```
