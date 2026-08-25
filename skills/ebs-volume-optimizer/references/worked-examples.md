# Worked Examples (load on demand) — EBS Volume Optimizer

Secondary worked examples and CLI/code patterns, moved verbatim from SKILL.md.


---

## Step 1: gp2 → gp3 and io1/io2 → gp3 migration CLI patterns (moved from SKILL.md)

#### gp2 → gp3 migration pattern

```bash
# Pre-modification snapshot (for rollback)
aws ec2 create-snapshot --volume-id <vol-id> \
  --description "pre-gp3-migration-$(date +%s)" \
  --tag-specifications "ResourceType=snapshot,Tags=[{Key=Name,Value=pre-gp3}]"

# Migrate gp2 → gp3 (online, no detach required)
aws ec2 modify-volume --volume-id <vol-id> --volume-type gp3

# Wait for modification to complete (check state)
aws ec2 describe-volumes-modifications --volume-id <vol-id> --output json | \
  jq '.VolumesModifications[] | {ModificationState, TargetVolumeType, Progress}'

# Post-modification: verify IOPS and throughput
aws ec2 describe-volumes --volume-ids <vol-id> --output json | \
  jq '.Volumes[] | {VolumeType, Iops, Throughput}'
```

#### io1/io2 → gp3 migration pattern

```bash
# Verify consumed IOPS is well below provisioned before migrating
aws cloudwatch get-metric-statistics --namespace AWS/EBS \
  --metric-name VolumeConsumedReadWriteOps \
  --dimensions Name=VolumeId,Value=<vol-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum \
  --output json | jq '.Datapoints | (map(.Average) | add / length) as $avg
    | (map(.Maximum) | max) as $max | {avg_consumed_iops: $avg, max_consumed_iops: $max}'

# If avg consumed < 50% of provisioned, migrate to gp3
# Set gp3 IOPS to the observed max consumed + 30% headroom
NEW_IOPS=$((MAX_CONSUMED * 13 / 10))  # 30% headroom, clamped to 3000-16000
NEW_IOPS=${NEW_IOPS//[^0-9]/}
if [ "$NEW_IOPS" -lt 3000 ]; then NEW_IOPS=3000; fi
if [ "$NEW_IOPS" -gt 16000 ]; then
  echo "Consumed IOPS > 16000 — cannot migrate to gp3 (cap). Stay on io2."
  exit 1
fi

aws ec2 modify-volume --volume-id <vol-id> \
  --volume-type gp3 --iops $NEW_IOPS
```

---

## Step 2: Downsize multi-step operation (moved from SKILL.md)

**Downsize is a multi-step operation:**
1. Create a new smaller volume of the target type.
2. Attach to the instance.
3. Copy data (e.g., `rsync -avx /old/ /new/` or `dd`).
4. Detach the old volume.
5. Mount the new volume at the old mount point.
6. Verify application functionality.
7. Delete the old volume (after confirmation).

---

## Step 3: gp3 IOPS optimization commands (moved from SKILL.md)

#### gp3 IOPS optimization

```bash
# Check if provisioned IOPS exceeds consumed
aws ec2 describe-volumes --volume-ids <vol-id> --output json | \
  jq '.Volumes[] | {Iops, Throughput}'

# If provisioned IOPS > 3000 (baseline) AND consumed < 50%, reduce to baseline
aws ec2 modify-volume --volume-id <vol-id> --iops 3000
```

---

## Step 4: DLM policy creation pattern (moved from SKILL.md)

#### DLM policy creation pattern

```bash
# Create a DLM policy for EBS snapshots
# Retention: 7 daily snapshots, 4 weekly snapshots
aws dlm create-lifecycle-policy \
  --description "EBS snapshot policy - 7 daily + 4 weekly" \
  --state ENABLED \
  --execution-role-arn arn:aws:iam::<acct>:role/AWSDataLifecycleManagerDefaultRole \
  --policy-details '{
    "PolicyType": "EBS_SNAPSHOT_MANAGEMENT",
    "ResourceTypes": ["VOLUME"],
    "TargetTags": [{"Key": "Backup", "Value": "daily"}],
    "Schedules": [
      {
        "Name": "DailySnapshots",
        "CopyTags": true,
        "CreateRule": {"Interval": 24, "IntervalUnit": "HOURS", "Times": ["03:00"]},
        "RetainRule": {"Count": 7}
      },
      {
        "Name": "WeeklySnapshots",
        "CopyTags": true,
        "CreateRule": {"Interval": 7, "IntervalUnit": "DAYS", "Times": ["03:00"]},
        "RetainRule": {"Count": 4}
      }
    ]
  }'
```

---

## Step 4: Snapshot Archive pattern (moved from SKILL.md)

#### Snapshot Archive pattern

```bash
# Archive a snapshot (retrieval takes 24-72 hours)
aws ec2 modify-snapshot-tier --snapshot-id snap-<id> --storage-tier archive

# Check archive status
aws ec2 describe-snapshots --snapshot-ids snap-<id> --output json | \
  jq '.Snapshots[] | {SnapshotId, StorageTier, ArchiveTierStartAt}'

# Retrieve from archive (if needed for restore)
aws ec2 restore-snapshot-tier --snapshot-id snap-<id> --storage-tier standard
```

---

## Step 5: Multi-attach commands (io2 only) (moved from SKILL.md)

```bash
# Check if the volume is io2 and has multi-attach enabled
aws ec2 describe-volumes --volume-ids <vol-id> --output json | \
  jq '.Volumes[] | {VolumeType, MultiAttachEnabled}'

# Enable multi-attach on an io2 volume
aws ec2 modify-volume --volume-id <vol-id> --multi-attach-enabled
```

---

## Step 6: Impact estimation formula (moved from SKILL.md)

```
current_monthly = (volume_GB × current_$/GB)
                + (current_provisioned_IOPS × $0.065, if io1)
                + (current_provisioned_IOPS × $0.005 × max(0, iops - 3000), if gp3)
                + (current_provisioned_MBps × $0.04 × max(0, mbps - 125), if gp3)
                + (snapshot_GB × $0.05)
                + (FSR_count × AZ_count × $0.06 × 730, if FSR enabled)

projected_monthly = (volume_GB × projected_$/GB)
                  + (projected_IOPS costs)
                  + (projected_snapshot_GB × $0.0125, if archived)
                  + (0, if FSR removed)

monthly_saving = current_monthly - projected_monthly
annual_saving = monthly_saving × 12
```

---

## Worked examples — io1→gp3, snapshot cleanup with Snapshot Archive, already optimal, NEED_MORE_INFO (moved from SKILL.md)

### Worked example — io1 over-provisioned IOPS to gp3

```text
TARGET: vol-0def456
VERDICT: OPPORTUNITY_FOUND
REASON: io1 1000 GB volume with 10000 provisioned IOPS is consuming only
  avg 1200 IOPS (12% utilization). Migrating to gp3 with 3000 baseline
  IOPS (2.5× the consumed headroom) eliminates the $650/month IOPS charge
  AND reduces the per-GB rate (Step 1 + Step 3).
RECOMMENDATION:
  Current: io1, 1000 GB, 10000 provisioned IOPS
  Proposed: gp3, 1000 GB, 3000 IOPS (baseline, free)
  Dimensions changed: type (Step 1) + IOPS (Step 3)
  Confidence: HIGH — VolumeConsumedReadWriteOps avg 1200, max 1800 over
    30 days. gp3 baseline 3000 provides 1.67× headroom over the max
    consumed. No instance-type constraint (attached to m5.2xlarge — Nitro).
ESTIMATED_SAVINGS:
  Current monthly: $775.00
    storage: 1000 GB × $0.125 = $125.00
    IOPS: 10000 × $0.065 = $650.00
  Projected monthly: $80.00
    storage: 1000 GB × $0.08 = $80.00
    IOPS: 3000 baseline (free), $0.00
  Monthly saving: $695.00 (90% reduction)
  Annual saving: $8,340.00
  Assumptions: us-east-1 pricing, gp3 baseline IOPS sufficient for
    observed workload (max 1800 < 3000 baseline).
MIGRATION_STEPS:
  1. Create a pre-modification snapshot:
     aws ec2 create-snapshot --volume-id vol-0def456
       --description "pre-gp3-migration-$(date +%s)"
  2. Modify the volume type and IOPS in one step:
     aws ec2 modify-volume --volume-id vol-0def456
       --volume-type gp3 --iops 3000
  3. Wait for modification to complete (check state).
  4. Verify: aws ec2 describe-volumes --volume-ids vol-0def456 --output json
       | jq '.Volumes[] | {VolumeType, Iops, Throughput}'
  5. Monitor VolumeQueueLength for 7 days post-change.
CONFIRM: Before modifying, emit and await:
  "CONFIRM: About to modify-volume vol-0def456 (io1 10000 IOPS → gp3 3000
   IOPS). Saving $695.00/month (90%). Online modification — no downtime.
   Proceed? (yes/no)"
```

### Worked example — snapshot cleanup with Snapshot Archive

```text
TARGET: vol-0ghi789 (and 145 associated snapshots)
VERDICT: OPPORTUNITY_FOUND
REASON: Volume has 145 snapshots accumulating without a deletion policy.
  Total snapshot storage: ~72,500 GB (145 × ~500 GB each) at $0.05/GB-mo
  = $3,625/month. No DLM or AWS Backup policy exists. Of these, 90
  snapshots are older than 90 days with no restore in 90 days — candidates
  for Snapshot Archive (75% cheaper). The remaining 55 snapshots should
  be governed by a DLM policy with 30-day retention (Step 4).
RECOMMENDATION:
  Current: 145 snapshots, no governance, $3,625/month
  Proposed: 55 snapshots (30-day DLM retention) + 90 archived snapshots
  Dimensions changed: snapshot governance + Snapshot Archive
  Confidence: HIGH — snapshot inventory and DLM policy absence confirmed;
    restore history confirms 0 restores in 90 days for the 90 old snapshots.
ESTIMATED_SAVINGS:
  Current monthly: $3,625.00 (72,500 GB × $0.05)
  Projected monthly: $1,018.75
    - 55 recent snapshots (27,500 GB × $0.05) = $1,375.00
    - 90 archived snapshots (45,000 GB × $0.0125) = $562.50
    Hmm, redo: projected is $1,375 + $562.50 = $1,937.50
    Wait — with DLM 30-day retention, only ~30 snapshots remain active.
    Recompute:
    - 30 daily snapshots (15,000 GB × $0.05) = $750.00
    - 90 archived snapshots (45,000 GB × $0.0125) = $562.50
    - Older-than-30-day non-archived snapshots deleted = $0
    Projected total: $1,312.50
  Monthly saving: $2,312.50 (64% reduction)
  Annual saving: $27,750.00
MIGRATION_STEPS:
  1. Create a DLM policy for future snapshot governance:
     aws dlm create-lifecycle-policy --description "vol-0ghi789 30-day"
       --state ENABLED ... (see Step 4 pattern)
  2. Archive the 90 snapshots older than 90 days:
     for snap in $(aws ec2 describe-snapshots --filters
       Name=volume-id,Values=vol-0ghi789 --output json |
       jq -r '.Snapshots[] | select(.StartTime < "2026-05-09") | .SnapshotId'); do
       aws ec2 modify-snapshot-tier --snapshot-id $snap --storage-tier archive
     done
  3. Delete snapshots older than 30 days that were NOT archived (the 25
     snapshots between 30-90 days old):
     CONFIRM before deleting — these are irrecoverable.
  4. Verify: aws ec2 describe-snapshots --filters Name=volume-id,Values=vol-0ghi789
       --output json | jq '.Snapshots | length'
CONFIRM: Before archiving and deleting, emit and await:
  "CONFIRM: About to archive 90 snapshots and delete 25 snapshots for
   vol-0ghi789. Saving $2,312.50/month. Archived snapshots take 24-72h
   to retrieve. Deleted snapshots are irrecoverable. Proceed? (yes/no)"
```

### Worked example — already optimal

```text
TARGET: vol-0jkl012
VERDICT: ALREADY_OPTIMAL
REASON: gp3 200 GB volume with baseline IOPS (3000) and throughput (125
  MB/s), right-sized (actual data 170 GB = 85%), governed by a 7-day DLM
  policy, no FSR, no multi-attach opportunity. All dimensions pass.
RECOMMENDATION:
  Current: gp3, 200 GB, 3000 IOPS, 125 MB/s, 7-day DLM — no change
  Dimensions checked: type ✓, capacity ✓, IOPS ✓, throughput ✓, snapshots ✓, FSR ✓
  Confidence: HIGH — 30-day metrics confirm stable performance; DLM policy
    active; no FSR configured.
ESTIMATED_SAVINGS:
  Monthly: $0.00
  Annual: $0.00
MIGRATION_STEPS:
  - None required. Continue monitoring CloudWatch metrics quarterly.
```

### Worked example — NEED_MORE_INFO (metrics absent)

```text
TARGET: vol-0mno345
VERDICT: NEED_MORE_INFO
REASON: VolumeQueueLength and VolumeReadOps/VolumeWriteOps metrics are
  absent for the requested 30-day window. The volume may be detached,
  recently created, or the IAM role may deny cloudwatch:GetMetricStatistics.
  Cannot make a type migration recommendation without I/O baseline data.
RECOMMENDATION:
  Current: gp2, 100 GB — pending data
  Proposed: pending data
  Confidence: LOW — no I/O metrics to evaluate.
ESTIMATED_SAVINGS:
  Monthly: $0 (cannot quantify without baseline)
MIGRATION_STEPS:
  1. Verify the volume is attached and receiving I/O:
     aws ec2 describe-volumes --volume-ids vol-0mno345 --output json
       | jq '.Volumes[].Attachments'
  2. Verify IAM permissions for CloudWatch:
     aws iam get-role-policy --role-name <role> --policy-name <policy>
  3. Wait 14-30 days for representative observation.
  4. Re-evaluate with VolumeQueueLength + VolumeReadOps/WriteOps data.
  Do NOT migrate based on assumed I/O patterns.
```

---

## Remediation guidance (moved from SKILL.md)

## Remediation guidance

### For OPPORTUNITY_FOUND — gp2 to gp3 migration

1. Create a pre-modification snapshot:
   `aws ec2 create-snapshot --volume-id <id> --description "pre-gp3-<ts>"`.
2. Modify the volume:
   `aws ec2 modify-volume --volume-id <id> --volume-type gp3`.
3. Wait for `ModificationState = completed` (check via
   `describe-volumes-modifications`).
4. Verify IOPS and throughput:
   `aws ec2 describe-volumes --volume-ids <id> --output json`.
5. Monitor `VolumeQueueLength` and application performance for 7 days.

### For OPPORTUNITY_FOUND — io1/io2 to gp3 migration

1. Create a pre-modification snapshot.
2. Verify `VolumeConsumedReadWriteOps` max is < 16,000 (gp3 cap).
3. Modify the volume type and IOPS in one step:
   `aws ec2 modify-volume --volume-id <id> --volume-type gp3 --iops <new>`.
4. Monitor VolumeQueueLength for 7 days.

### For OPPORTUNITY_FOUND — IOPS right-size (gp3)

1. Modify the IOPS:
   `aws ec2 modify-volume --volume-id <id> --iops 3000`.
2. Monitor VolumeQueueLength for 7 days.

### For OPPORTUNITY_FOUND — snapshot governance (DLM)

1. Create a DLM policy (see Step 4 pattern).
2. Tag the volume for DLM targeting:
   `aws ec2 create-tags --resources <vol-id> --tags Key=Backup,Value=daily`.
3. Verify the first DLM-created snapshot appears within 24 hours.

### For OPPORTUNITY_FOUND — Snapshot Archive

1. Archive old snapshots:
   `aws ec2 modify-snapshot-tier --snapshot-id <snap> --storage-tier archive`.
2. Verify archive status:
   `aws ec2 describe-snapshots --snapshot-ids <snap> --output json`.
3. Note: archived snapshots take 24-72 hours to retrieve if needed.

### For OPPORTUNITY_FOUND — FSR removal

1. Disable FSR:
   `aws ec2 disable-fast-snapshot-restores --availability-zones <az> --snapshot-ids <snap>`.
2. Verify FSR state transitions to `disabled` then `disabling`.

### For ALREADY_OPTIMAL or OPTIMIZED

1. No remediation required for the current posture.
2. Recommend quarterly review of CloudWatch metrics and DLM policies.
3. Re-evaluate when workload I/O patterns change or new EBS types launch.
