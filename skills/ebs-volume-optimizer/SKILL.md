---
name: ebs-volume-optimizer
description: >-
  Optimises EBS volume cost across six dimensions: volume type migration
  (gp2 to gp3 is 20% cheaper with higher baseline IOPS; io1/io2 to gp3
  when provisioned IOPS are unused; st1/sc1 for sequential and cold
  workloads), capacity right-sizing (downsize volumes where actual data is
  much smaller than provisioned), IOPS/throughput optimization (gp3 baseline
  3000 IOPS + 125 MB/s free; detect over-provisioned io1/io2), snapshot
  hygiene (automate deletion via DLM/AWS Backup; Snapshot Archive is 75%
  cheaper; FSR is expensive and only for boot volumes), io2 multi-attach
  consolidation, and impact estimation with dollar savings. Emits
  OPPORTUNITY_FOUND with specific recommendation and estimated savings,
  OPTIMIZED, or ALREADY_OPTIMAL. Use when reviewing EBS spend, planning a
  gp2-to-gp3 migration sweep, auditing snapshot accumulation, or building a
  storage FinOps savings plan.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline recommendation classification works from pasted volume
  configuration and CloudWatch metrics. Live-account optimization uses aws
  ec2 describe-volumes, aws ec2 describe-volume-attribute, aws ec2
  describe-volumes-modifications, aws cloudwatch get-metric-statistics
  (VolumeReadBytes, VolumeWriteBytes, VolumeReadOps, VolumeWriteOps,
  VolumeQueueLength, VolumeThroughputPercentage, VolumeConsumedReadWriteOps),
  aws ec2 describe-snapshots, aws backup list-backup-plans, aws dlm
  get-lifecycle-policies, and aws ce get-cost-and-usage (AWS CLI v2, SSO or
  key-based credentials). Pricing references us-east-1 published rates as
  of 2026; re-state regional rates from the reference matrix for other
  regions.
keywords:
  - EBS
  - gp3
  - gp2
  - io1
  - io2
  - st1
  - sc1
  - volume type migration
  - right-sizing
  - IOPS
  - throughput
  - provisioned IOPS
  - burst credits
  - snapshot
  - Snapshot Archive
  - Fast Snapshot Restore
  - FSR
  - DLM
  - AWS Backup
  - multi-attach
  - VolumeQueueLength
  - cost optimization
  - FinOps
tags: [ebs, storage, cost-optimization, finops, gp3, snapshot, right-sizing, volume-type]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Storage
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL"
  when_to_use: >-
    Optimising EBS volume cost, planning a gp2-to-gp3 migration sweep,
    auditing snapshot accumulation, right-sizing volume capacity, tuning
    provisioned IOPS on io1/io2 volumes, evaluating Snapshot Archive or
    Fast Snapshot Restore, consolidating volumes via io2 multi-attach, or
    building a storage FinOps savings plan.
  when_not_to_use: >-
    S3 storage cost (use s3-lifecycle-optimizer), EC2 instance rightsizing
    (use ec2-rightsizing-optimizer), Lambda cost (use
    lambda-cost-optimizer), or EBS performance troubleshooting (use the
    EC2/EBS troubleshooter). This skill focuses on cost-driven volume
    optimization decisions, not performance debugging.
  activation_triggers:
    - "optimise EBS volume cost"
    - "gp2 to gp3 migration"
    - "EBS volume right-sizing"
    - "EBS snapshot cleanup"
    - "provisioned IOPS unused"
    - "io1 to gp3 migration"
    - "EBS Snapshot Archive"
    - "Fast Snapshot Restore cost"
    - "EBS multi-attach consolidation"
    - "EBS burst credits exhausted"
    - "VolumeQueueLength high"
    - "EBS FinOps savings"
    - "EBS monthly savings estimate"
    - "reduce EBS bill"
    - "storage cost review"
  invocation_schema: >-
    Input: either (a) a volume identifier + live-account context, (b) a
    volume configuration document (volume type, size, IOPS, throughput,
    attached instance), OR (c) CloudWatch EBS metrics (VolumeReadBytes,
    VolumeWriteBytes, VolumeReadOps, VolumeWriteOps, VolumeQueueLength)
    with at least 14 days of observation. Output: a deterministic
    TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS
    block per volume, where VERDICT is one of OPTIMIZED,
    OPPORTUNITY_FOUND, ALREADY_OPTIMAL.
  invocation_example: |-
    # Minimal valid input (offline finding classification):
    VolumeId: vol-0abc123
    VolumeType: gp2
    Size: 500 GB
    Region: us-east-1
    IOPS: 1500 (baseline for gp2 at this size)
    Attached instance: i-prod-db-01 (PostgreSQL primary)
    Metrics (last 30 days):
      - VolumeReadOps + VolumeWriteOps: avg 250/s, max 400/s
      - VolumeQueueLength: avg 0.2, max 0.8
      - VolumeReadBytes + VolumeWriteBytes: avg 8 MB/s, max 15 MB/s
    Emit the standard optimization block (TARGET, VERDICT, REASON,
    RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).
---

# EBS Volume Optimizer

## What this skill does

Translates an EBS volume's configuration and utilization posture into a
concrete cost-optimization recommendation with a dollar-denominated
savings estimate. The verdict is the highest-leverage action across six
dimensions — volume type migration, capacity right-sizing, IOPS/throughput
tuning, snapshot hygiene, multi-attach consolidation, and workload
placement — applied in priority order. Always pairs the recommendation
with the exact CLI commands so the operator can review, confirm, and apply.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and pricing table | First read |
| Mindset / Philosophy | Why gp3 is the default; provisioned-IOPS waste; snapshot accumulation | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a volume |
| Pre-flight data gate | CloudWatch metrics, volume config, snapshot inventory | Before any recommendation |
| Step 0 non-obvious behaviours | gp2 burst credits, gp3 IOPS caps, modification cooldown, FSR cost | Edge cases |
| Step 1 Volume type migration | gp2→gp3, io1/io2→gp3, st1/sc1 selection | The headline savings dimension |
| Step 2 Capacity right-sizing | Downsize volumes where data << provisioned | Oversized volumes |
| Step 3 IOPS/throughput optimization | gp3 baseline, io2 Block Express, over-provisioned IOPS | Provisioned-IOPS volumes |
| Step 4 Snapshot optimization | DLM, AWS Backup, Snapshot Archive, FSR | Snapshot accumulation |
| Step 5 Multi-attach (io2) | Consolidate volumes across instances | Shared storage |
| Step 6 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, pre-modification snapshot, detached state | Before any apply CLI |

## Quick start

- **gp3 is the default.** gp3 is 20% cheaper than gp2 ($0.08/GB vs
  $0.10/GB) AND provides baseline 3000 IOPS + 125 MB/s (vs gp2's burst-
  credit system that starves small volumes). gp3 is strictly better for
  most workloads. Migrate all gp2 volumes unless there is a documented
  reason not to.
- **Provisioned IOPS (io1/io2) is the #2 waste line.** io1/io2 charge per
  provisioned-IOPS-month ($0.065/IOPS for io1). If `VolumeConsumedReadWriteOps`
  is consistently < 50% of provisioned IOPS, migrate to gp3 and save both
  the per-GB and per-IOPS cost.
- **Snapshots accumulate silently.** EBS snapshots are incremental but
  billed at full size ($0.05/GB-month). A volume with 100 snapshots
  averaging 500 GB each bills ~$2,500/month in snapshot storage alone.
  Automate deletion with DLM or AWS Backup; archive rarely-accessed
  snapshots to Snapshot Archive (75% cheaper at $0.0125/GB-month).
- **Cost formula (memorise this):**
  ```
  monthly_cost = (volume_GB × $/GB_rate)
               + (provisioned_IOPS × $/IOPS_rate, if io1/io2/gp3-extra)
               + (provisioned_MBps × $/MBps_rate, if gp3-extra)
               + (snapshot_GB × $0.05)
               + (FSR: $0.06/hour per AZ, if enabled)
  ```

## Mindset

EBS cost optimization is a price-performance decision driven by observed
I/O patterns, not by provisioned specs. The goal is the cheapest volume
type and size that comfortably handles peak IOPS and throughput without
queue-length regression — not the absolute minimum that satisfies the
average. A type migration that triples `VolumeQueueLength` costs more in
application latency than it saves in EBS dollars. The decision framework
below favours conservatism: validate I/O headroom before migrating, and
always provide a rollback path via a pre-modification snapshot.

## Philosophy

Four behaviours separate a senior storage FinOps engineer from a generalist:

- **gp3 is the right default for almost everything.** gp3 delivers
  baseline 3000 IOPS and 125 MB/s at no extra cost — better than gp2's
  burst-credit system for small volumes (gp2 under 1 TB earns only
  100-3000 IOPS in burst credits). The 20% per-GB discount is on top of
  the performance improvement. Migrating gp2 → gp3 is the single highest-
  leverage EBS optimization.

- **Provisioned IOPS is insurance that is rarely cashed in.** io1/io2
  volumes charge per provisioned-IOPS-month regardless of actual usage.
  Most io1/io2 volumes are provisioned at the peak IOPS the workload
  MIGHT need someday, then never actually hit that peak. Checking
  `VolumeConsumedReadWriteOps` against provisioned IOPS typically reveals
  40-80% over-provisioning. Migrating to gp3 (with extra IOPS if needed)
  is almost always cheaper.

- **Snapshot accumulation is invisible until the bill arrives.** EBS
  snapshots are incremental at the block level but billed at full size.
  An organization that creates daily snapshots and never deletes them
  accumulates snapshot storage faster than volume storage. The fix is
  automated lifecycle policies (DLM or AWS Backup), not manual cleanup.

- **Fast Snapshot Restore (FSR) is the most expensive EBS feature per
  unit.** FSR charges $0.06/hour per AZ per snapshot — that is
  $43.20/month per AZ per snapshot. FSR is justified ONLY for boot
  volumes that must be instantly available after instance launch (e.g.,
  auto-scaling groups with strict warmup requirements). Using FSR for
  data volumes or rarely-launched instances is pure waste.

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| VolumeType = gp2 | **OPPORTUNITY_FOUND** (type migration) | Step 1 — migrate to gp3 (20% cheaper, better baseline) |
| VolumeType = io1/io2 AND VolumeConsumedReadWriteOps < 50% of provisioned IOPS sustained | **OPPORTUNITY_FOUND** (type migration) | Step 1 — migrate to gp3 (saves per-GB + per-IOPS) |
| Volume size >> actual data (VolumeReadBytes+WriteBytes sustained low) AND gp2 burst credits exhausted | **OPPORTUNITY_FOUND** (capacity + type) | Step 2 — downsize + migrate to gp3 with higher IOPS |
| gp3 volume with provisioned IOPS > 3000 AND VolumeConsumedReadWriteOps < 50% of provisioned | **OPPORTUNITY_FOUND** (IOPS right-size) | Step 3 — reduce provisioned IOPS to baseline 3000 |
| io1/io2 volume with provisioned IOPS >> actual (over-provisioned) | **OPPORTUNITY_FOUND** (IOPS right-size or migrate) | Step 3 — reduce IOPS OR migrate to gp3 |
| Snapshots with no deletion policy AND total snapshot GB > volume GB | **OPPORTUNITY_FOUND** (snapshot cleanup) | Step 4 — DLM/AWS Backup policy with retention |
| Snapshots older than 90 days with no restore in 90 days | **OPPORTUNITY_FOUND** (Snapshot Archive) | Step 4 — archive to save 75% |
| FSR enabled on a data volume OR on a snapshot rarely restored | **OPPORTUNITY_FOUND** (FSR removal) | Step 4 — remove FSR ($43.20/AZ/month waste) |
| Multiple io2 volumes attached to instances in the same cluster | **OPPORTUNITY_FOUND** (multi-attach) | Step 5 — consolidate via io2 multi-attach |
| VolumeType = gp3, IOPS ≤ 3000 (baseline), right-sized, snapshots governed by DLM | **ALREADY_OPTIMAL** | None — continue monitoring |
| VolumeReadBytes/WriteBytes or VolumeQueueLength metrics absent | **NEED_MORE_INFO** | Pull 14-30 day CloudWatch data, re-evaluate |
| A change was applied and verified this session | **OPTIMIZED** | Emit post-state verification |

See the ordered steps for edge cases (st1/sc1 workload fit, io2 Block
Express, cross-zone modification constraints).

## Pre-flight: data gate (run before any optimization decision)

EBS optimization decisions depend on observed I/O patterns. Several data-
quality conditions short-circuit the recommendation.

### Required data sources

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

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `VolumeQueueLength` metric absent | **NEED_MORE_INFO**: cannot assess if the current IOPS is sufficient. The volume may be detached or very recently created. |
| Observation window < 14 days | **NEED_MORE_INFO**: I/O may reflect atypical load. Minimum 14 days; 30 days preferred. |
| Volume `State != in-use` (detached) | Detached volumes still bill for storage. Surface as an OPPORTUNITY_FOUND (delete if unused) or NEED_MORE_INFO (confirm intent). |
| Volume `State = error` or `recovering` | Surface as BLOCKED — resolve the volume health before optimizing cost. |
| `VolumeConsumedReadWriteOps` absent on io1/io2 | Fall back to `VolumeReadOps + VolumeWriteOps`; mark IOPS recommendation as MEDIUM confidence. |
| Snapshots exist but no DLM/AWS Backup policy | Surface as OPPORTUNITY_FOUND on the snapshot dimension regardless of other findings. |

## Process — Optimization logic (apply in order, aggregate all applicable)

### Step 0: Non-obvious behaviours that change the recommendation

These are the operational gotchas a senior storage engineer knows from
production experience — each one routes a recommendation away from the
obvious choice:

- **gp2 burst credits are per-volume, not per-instance.** A gp2 volume
  earns burst credits based on its size: larger volumes earn more credits
  per second and have a larger credit balance. Small gp2 volumes (< 1 TB)
  have very low baseline IOPS (100-1000) and exhaust burst credits quickly
  under sustained load. The symptom is intermittent I/O throttle that
  does NOT appear in average metrics — check `BurstBalance` minimums. gp3
  eliminates this by providing 3000 IOPS baseline regardless of size.

- **gp3 IOPS and throughput caps.** gp3 supports up to 16,000 IOPS and
  1,000 MB/s. The baseline (free) is 3,000 IOPS and 125 MB/s. Additional
  IOPS cost $0.005/provisioned-IOPS-month; additional throughput costs
  $0.04/provisioned-MBps-month. If a workload needs > 16,000 IOPS, it
  MUST stay on io2 (up to 256,000 IOPS with Block Express).

- **Volume modification has a cooldown and performance impact.** AWS
  allows modifying volume type, size, and IOPS online (no detach
  required), but the modification takes effect gradually (usually within
  6 hours, sometimes up to 24 hours). During the modification, the volume
  may experience brief performance variations. Always warn the operator.

- **You MUST wait for the previous modification to complete before
  starting a new one.** AWS allows only one pending modification per
  volume. Attempting a second modification while the first is in progress
  returns `InvalidVolumeModification`. Check
  `aws ec2 describe-volumes-modifications` before starting a new
  modification.

- **Volume size increases are instant; decreases require a support
  request.** Increasing volume size is a self-service operation.
  Decreasing volume size (`modify-volume` to a smaller size) is NOT
  supported via the standard API — you must create a new smaller volume,
  copy the data (e.g., via `dd` or `rsync`), detach the old, attach the
  new. Surface this as a higher-effort remediation.

- **io2 Block Express is not available on all instance types.** io2
  Block Express delivers up to 256,000 IOPS and 4,000 MB/s, but requires
  Nitro-based instances (m5/c5/r5 and later). Older instance types
  (m3/c3/m4/c4) are limited to standard io2 (64,000 IOPS max). Check the
  attached instance type before recommending io2 Block Express.

- **Snapshot deletion does not delete data from prior snapshots.** EBS
  snapshots are incremental — each snapshot only stores the blocks that
  changed since the previous snapshot. Deleting an intermediate snapshot
  merges its data into the next snapshot. Deleting the MOST RECENT
  snapshot is always safe (no data loss). Deleting older snapshots is
  also safe but may slow down restoration from the remaining chain.

- **Snapshot Archive retrieval takes 24-72 hours.** Snapshot Archive is
  75% cheaper ($0.0125/GB-month vs $0.05/GB-month for standard) but
  retrieving an archived snapshot takes 24-72 hours. Do NOT archive
  snapshots that might be needed for disaster recovery within 72 hours.
  Archive only for compliance / long-term retention.

- **Fast Snapshot Restore (FSR) charges per-AZ, per-snapshot, per-hour.**
  FSR is $0.06/hour per AZ per snapshot = $43.20/month per AZ per
  snapshot. If FSR is enabled on 10 snapshots across 3 AZs, that is
  $1,296/month just for FSR. FSR is justified ONLY for boot volumes that
  must be instantly available after instance launch (e.g., auto-scaling
  groups with strict warmup requirements).

- **EBS optimization is built into all current-gen instances.** m5/c5/r5
  and later include EBS-optimized networking at no extra cost. Legacy
  instances (m4.16xlarge, c4.10xlarge) may charge for EBS-optimized
  status. A migration from legacy to current-gen unlocks "free" EBS
  optimization in addition to other savings.

- **Multi-attach is io2 only (and io2 Block Express).** Up to 16 Nitro-
  based EC2 instances can concurrently access a single io2 volume. This
  is useful for cluster-aware file systems (OCFS2, GFS2) and shared-disk
  database clusters (Oracle RAC). Multi-attach does NOT work on gp2/gp3/
  st1/sc1. Do not recommend multi-attach on non-io2 volume types.

- **st1 (Throughput Optimized HDD) cannot be a boot volume.** st1 is for
  data volumes only — sequential workloads like data warehouses, log
  processing, and big data. It is cheaper than gp3 ($0.045/GB vs
  $0.08/GB) but has higher latency and cannot be used as a boot device.

- **sc1 (Cold HDD) is the cheapest EBS tier ($0.015/GB).** Designed for
  infrequently accessed data (archives, backups stored on EBS). sc1
  provides ~12 MB/s per TB of baseline throughput — sufficient for
  archival retrieval but too slow for any active workload.

- **Encrypted volumes cannot be shared across accounts.** KMS-encrypted
  volumes use a customer-managed key that is account-specific. If the
  volume is shared across accounts (e.g., in an organization), the KMS
  key policy must allow cross-account access. Volume type migration does
  not change the encryption status.

### Step 1: Volume type migration

Volume type migration is the headline savings dimension. The decision
matrix below routes each volume type to its optimal target.

#### Migration decision matrix

| Current type | Target type | Saving | When to migrate | When NOT to migrate |
|---|---|---|---|---|
| gp2 | gp3 | 20% per-GB + better baseline IOPS | Almost always — gp3 is strictly better for most workloads | Workload needs > 16,000 IOPS (gp3 cap) — but then you should be on io2, not gp2 |
| io1 | gp3 | Per-GB + per-IOPS elimination | VolumeConsumedReadWriteOps < 50% of provisioned IOPS sustained | Workload genuinely needs > 16,000 IOPS or sub-millisecond latency |
| io1 | io2 | Same price, better durability | io1 with critical data (io2 is 99.999% durability vs io1's 99.8-99.9%) | N/A — io2 is a superset of io1 |
| io2 (high IOPS) | io2 Block Express | Per-IOPS savings at scale | Workload needs > 64,000 IOPS (standard io2 cap) | Attached to a non-Nitro instance |
| gp3 (if high throughput needed) | st1 | 44% cheaper ($0.045 vs $0.08) | Sequential workload (data warehouse, log processing, Hadoop) | Workload needs random I/O or is a boot volume |
| gp3 (if rarely accessed) | sc1 | 81% cheaper ($0.015 vs $0.08) | Infrequently accessed data (archives, cold backups) | Any active workload (sc1 throughput is too low) |

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

### Step 2: Capacity right-sizing

Volume size right-sizing identifies volumes where the provisioned capacity
is significantly larger than the actual data stored.

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

#### Right-sizing decision table

| Observation | Verdict | Action |
|---|---|---|
| Actual data < 50% of provisioned size | **OPPORTUNITY_FOUND** (downsize) | Create a new smaller volume, copy data, swap. Surface as higher-effort remediation. |
| Actual data 50-80% of provisioned size | MEDIUM — consider downsize at next maintenance | Not urgent; monitor growth trend. |
| Actual data > 80% of provisioned size | ALREADY_OPTIMAL (capacity) | Size is appropriate; do not downsize. |
| gp2 with BurstBalance chronically near 0 | **OPPORTUNITY_FOUND** (migrate to gp3) | gp2 burst credits exhausted — switch to gp3 for higher baseline IOPS. |

**Downsize is a multi-step operation:**
1. Create a new smaller volume of the target type.
2. Attach to the instance.
3. Copy data (e.g., `rsync -avx /old/ /new/` or `dd`).
4. Detach the old volume.
5. Mount the new volume at the old mount point.
6. Verify application functionality.
7. Delete the old volume (after confirmation).

### Step 3: IOPS/throughput optimization

For gp3 and io1/io2 volumes, provisioned IOPS and throughput may be
over-spec'd relative to actual usage.

#### gp3 IOPS optimization

```bash
# Check if provisioned IOPS exceeds consumed
aws ec2 describe-volumes --volume-ids <vol-id> --output json | \
  jq '.Volumes[] | {Iops, Throughput}'

# If provisioned IOPS > 3000 (baseline) AND consumed < 50%, reduce to baseline
aws ec2 modify-volume --volume-id <vol-id> --iops 3000
```

| Observation | Verdict | Action |
|---|---|---|
| gp3 with IOPS > 3000 AND VolumeConsumedReadWriteOps avg < 1500 (50% of baseline) | **OPPORTUNITY_FOUND** (reduce IOPS to baseline) | Set IOPS to 3000 (free baseline). Saving: `(current_IOPS - 3000) × $0.005`/month. |
| gp3 with Throughput > 125 AND observed throughput < 60 MB/s | **OPPORTUNITY_FOUND** (reduce throughput to baseline) | Set Throughput to 125 (free baseline). Saving: `(current_MBps - 125) × $0.04`/month. |
| io1/io2 with provisioned IOPS >> consumed | **OPPORTUNITY_FOUND** (reduce IOPS or migrate to gp3) | Reduce IOPS to consumed_max × 1.3, OR migrate to gp3 if consumed < 16,000. |

#### io2 Block Express evaluation

io2 Block Express delivers up to 256,000 IOPS and 4,000 MB/s. Use it
ONLY for extreme OLTP workloads (e.g., Oracle RAC, SAP HANA) that require
both high IOPS and sub-millisecond latency. Check the attached instance
type — Block Express requires Nitro-based instances.

```bash
# Check if the instance is Nitro-based (required for Block Express)
aws ec2 describe-instances --instance-ids <instance-id> --output json | \
  jq '.Reservations[].Instances[] | .InstanceType'

# Nitro instances: m5+, c5+, r5+, p3+, inf1+, and all later generations
# Non-Nitro: m3, c3, m4 (most), c4 — cannot use Block Express
```

### Step 4: Snapshot optimization

Snapshots are a major cost line that accumulates silently.

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

#### Snapshot optimization decision matrix

| Observation | Verdict | Action |
|---|---|---|
| Snapshots exist with no DLM or AWS Backup policy | **OPPORTUNITY_FOUND** (snapshot governance) | Create DLM policy with retention (e.g., keep 7 daily, 4 weekly). |
| Snapshots older than 90 days with no restore in 90 days | **OPPORTUNITY_FOUND** (Snapshot Archive) | Archive to save 75% ($0.0125 vs $0.05/GB-month). |
| FSR enabled on data volumes (not boot volumes) | **OPPORTUNITY_FOUND** (FSR removal) | Remove FSR — $43.20/AZ/month per snapshot. Only justified for boot volumes. |
| FSR enabled across multiple AZs but the volume is in one AZ | **OPPORTUNITY_FOUND** (FSR right-size) | Remove FSR from AZs that don't launch instances from this snapshot. |
| Daily snapshots with indefinite retention | **OPPORTUNITY_FOUND** (retention cap) | Set retention to 30-90 days; archive older snapshots. |

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

### Step 5: Multi-attach consolidation (io2 only)

If multiple EC2 instances in the same cluster each have their own io2
volume for shared data, they may be candidates for consolidation via io2
multi-attach.

```bash
# Check if the volume is io2 and has multi-attach enabled
aws ec2 describe-volumes --volume-ids <vol-id> --output json | \
  jq '.Volumes[] | {VolumeType, MultiAttachEnabled}'

# Enable multi-attach on an io2 volume
aws ec2 modify-volume --volume-id <vol-id> --multi-attach-enabled
```

**Multi-attach decision:**

| Observation | Verdict | Action |
|---|---|---|
| 2+ io2 volumes attached to instances in the same cluster with similar data | **OPPORTUNITY_FOUND** (consolidation) | Consolidate to one io2 volume with multi-attach. Saves N-1 volumes. |
| Cluster-aware file system (OCFS2, GFS2) in use | Multi-attach is safe | Proceed with consolidation. |
| No cluster-aware file system | Multi-attach is UNSAFE | Do NOT enable multi-attach without a cluster-aware file system — concurrent writes will corrupt data. |

### Step 6: Impact estimation

Compute the monthly savings for each recommendation:

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

**Pricing reference (us-east-1, 2026):**

| Volume type | $/GB-month | $/IOPS-month | $/MBps-month | Max IOPS | Max throughput |
|---|---|---|---|---|---|
| gp3 | $0.08 | $0.005 (above 3000 baseline) | $0.04 (above 125 baseline) | 16,000 | 1,000 MB/s |
| gp2 | $0.10 | included | included | 16,000 (burst) | varies by size |
| io1 | $0.125 | $0.065 | included | 64,000 | 1,000 MB/s |
| io2 | $0.125 | $0.065 | included | 64,000 (256,000 Block Express) | 4,000 MB/s |
| st1 | $0.045 | included | included | 500 per TB | 500 MB/s per TB |
| sc1 | $0.015 | included | included | 250 per TB | 250 MB/s per TB |
| Snapshot (standard) | $0.05/GB-month | — | — | — | — |
| Snapshot Archive | $0.0125/GB-month | — | — | — | — |
| FSR | $0.06/hour per AZ per snapshot | — | — | — | — |

### Step 7: Final verdict

The verdict is the worst-case (most-actionable) finding across all
dimensions:

- If any dimension recommends a change (type migration, capacity right-
  size, IOPS/throughput tuning, snapshot cleanup, multi-attach, FSR
  removal), verdict is **OPPORTUNITY_FOUND**.
- If all dimensions pass AND the volume is already on gp3 (or the optimal
  type for its workload) AND snapshots are governed AND no FSR waste,
  verdict is **ALREADY_OPTIMAL**.
- If a change was applied and verified this session, verdict is
  **OPTIMIZED**.
- If data is insufficient (VolumeQueueLength metrics absent, window < 14
  days), verdict is **NEED_MORE_INFO**.

## Output format

```text
TARGET: <volume-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <type> <size>GB, <IOPS> IOPS, <throughput> MB/s in <region>
  Proposed: <type> <size>GB, <IOPS> IOPS, <throughput> MB/s in <region>
  Dimensions changed: <type | capacity | iops | throughput | snapshot | fsr | multi-attach>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list (pricing region, 730h/month, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <volume-id> in <region>.
  Proceed? (yes/no)"
```

### Worked example — gp2 to gp3 migration

```text
TARGET: vol-0abc123
VERDICT: OPPORTUNITY_FOUND
REASON: gp2 500 GB volume attached to a PostgreSQL primary is a clear
  migration candidate. gp3 is 20% cheaper ($0.08 vs $0.10/GB) AND provides
  3000 baseline IOPS (vs gp2's size-based 1500 baseline). BurstBalance
  shows chronic depletion during peak hours — gp3 eliminates the burst
  credit cliff (Step 1).
RECOMMENDATION:
  Current: gp2, 500 GB, ~1500 baseline IOPS (size-based), no provisioned throughput
  Proposed: gp3, 500 GB, 3000 IOPS (baseline), 125 MB/s (baseline)
  Dimensions changed: type (Step 1)
  Confidence: HIGH — VolumeQueueLength stable (< 1), no IOPS bottleneck
    at gp3 baseline; BurstBalance chronically < 20% confirming gp2
    underperformance.
ESTIMATED_SAVINGS:
  Current monthly: $50.00 (500 GB × $0.10)
  Projected monthly: $40.00 (500 GB × $0.08)
  Monthly saving: $10.00 (20% reduction)
  Annual saving: $120.00
  Assumptions: us-east-1 pricing, no size change, IOPS within gp3 baseline.
MIGRATION_STEPS:
  1. Create a pre-modification snapshot:
     aws ec2 create-snapshot --volume-id vol-0abc123
       --description "pre-gp3-migration-$(date +%s)"
  2. Modify the volume type (online, no detach required):
     aws ec2 modify-volume --volume-id vol-0abc123 --volume-type gp3
  3. Wait for modification to complete:
     aws ec2 describe-volumes-modifications --volume-ids vol-0abc123
       --output json | jq '.VolumesModifications[].ModificationState'
     (State should reach "completed" within 6 hours)
  4. Verify IOPS and throughput:
     aws ec2 describe-volumes --volume-ids vol-0abc123 --output json
       | jq '.Volumes[] | {VolumeType, Iops, Throughput}'
  5. Monitor VolumeQueueLength and BurstBalance (now N/A for gp3) for 7 days.
CONFIRM: Before modifying, emit and await:
  "CONFIRM: About to modify-volume vol-0abc123 (gp2 → gp3). Saving
   $10.00/month. Online modification — no downtime. Proceed? (yes/no)"
```

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

## Verdict semantics — reconciling the verdict_shape

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one dimension has a concrete, savings-bearing recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | A change was applied and verified this session; metrics confirm the new config lands within healthy performance bands. | Primary — only emitted post-remediation. |
| `ALREADY_OPTIMAL` | All dimensions pass (volume on optimal type, capacity right-sized, IOPS within baseline, snapshots governed, no FSR waste). | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Data gate failed: VolumeQueueLength metrics absent, observation window < 14 days, or volume detached with no I/O history. | Pre-decision — emit before any recommendation. |
| `BLOCKED` | Volume `State = error` or `recovering`; IAM denies `ec2:DescribeVolumes`; or the volume is in a failed state. | Pre-decision — emit when no reliable signal exists. |

## Verdict consistency rules

1. **Zero-savings rule.** If `MONTHLY_SAVING == $0.00` for every
   dimension, the verdict MUST be `ALREADY_OPTIMAL`.

2. **Negative-savings rule.** If the projected monthly cost is HIGHER than
   current (e.g., migrating from st1 to gp3 for a sequential workload),
   the verdict for that dimension is "no action."

3. **OPPORTUNITY_FOUND requires positive savings.** When emitting
   `OPPORTUNITY_FOUND`, the SAVINGS block must show positive
   `MONTHLY_SAVING` for at least one dimension.

4. **SAVINGS arithmetic check.** `CURRENT_MONTHLY − PROJECTED_MONTHLY`
   MUST equal `MONTHLY_SAVING`.

5. **gp2 → gp3 is almost always OPPORTUNITY_FOUND** unless the workload
   needs > 16,000 IOPS (in which case the volume should be on io2, not
   gp2). A gp2 volume with no finding on the type dimension is suspicious
   — double-check the IOPS requirement.

6. **Snapshot dimension coverage.** Every verdict block MUST address the
   snapshot dimension, even if the finding is "snapshots are governed by
   DLM, no action." Omitting the snapshot dimension implies it was not
   evaluated.

## Error handling — CLI and data-source failures

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-metric-statistics` returns empty `Datapoints` for VolumeQueueLength | `len(Datapoints) == 0` | Verdict: `NEED_MORE_INFO`. Reason: "Volume may be detached or recently created. No I/O signal." |
| `VolumeConsumedReadWriteOps` absent on io1/io2 | `list-metrics` returns no match | Fall back to `VolumeReadOps + VolumeWriteOps`; mark IOPS recommendation as MEDIUM confidence. |
| `BurstBalance` absent on gp2 | Metric not published for gp2 volumes < 1 TB in some cases | Cannot assess burst credit exhaustion. Proceed with type migration recommendation based on per-GB savings alone; note BurstBalance data unavailable. |
| CloudWatch API throttling | Exit code non-zero, stderr contains "Throttling" | Retry with exponential backoff (`--max-attempts 5`). |

### EC2 API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-volumes` returns `InvalidVolume.NotFound` | API error | Volume does not exist. Skip entirely. |
| `modify-volume` fails with `InvalidVolumeModification` | API error | Another modification is in progress. Wait for `ModificationState = completed`, retry. |
| `modify-volume` fails with `VolumeModificationRateExceeded` | API error | Too many modifications in a short window. Wait 5 minutes, retry. |
| `modify-volume` for size decrease fails | API error | Size decrease is NOT supported via standard API. Surface as a higher-effort remediation (create new smaller volume, copy data, swap). |
| `modify-snapshot-tier` fails with `InvalidSnapshot.NotFound` | API error | Snapshot does not exist or has been deleted. Skip; update snapshot inventory. |
| `describe-fast-snapshot-restores` returns empty | `len(FastSnapshotRestores) == 0` | No FSR configured — this is GOOD. No FSR dimension finding. |

### DLM / AWS Backup failures

| Failure mode | Detection | Handling |
|---|---|---|
| `dlm get-lifecycle-policies` returns empty | `len(Policies) == 0` | No DLM policies exist in the account. Surface snapshot governance as OPPORTUNITY_FOUND on any volume with snapshots. |
| `backup list-backup-plans` returns empty | `len(BackupPlansList) == 0` | No AWS Backup plans. Do NOT block — DLM may be the right tool for EBS-only governance. |
| DLM policy creation fails with `AccessDeniedException` | API error | The role lacks `dlm:CreateLifecyclePolicy`. Surface the IAM requirement in MIGRATION_STEPS. |

## Anti-Patterns — NEVER

- NEVER recommend migrating from gp2/gp3 to io1/io2 without confirming the
  workload genuinely needs > 16,000 IOPS. io1/io2 is 56% more expensive
  per GB ($0.125 vs $0.08) PLUS $0.065/IOPS-month. Recommending it for a
  workload that doesn't need it is a massive cost increase.

- NEVER migrate io1/io2 to gp3 if `VolumeConsumedReadWriteOps` max is
  within 20% of the gp3 cap (16,000 IOPS). The workload is genuinely IOPS-
  bound and needs io1/io2. Migrating to gp3 will cause performance
  degradation.

- NEVER recommend decreasing volume size as a simple API call. AWS does
  NOT support `modify-volume` to a smaller size via the standard API.
  Downsizing requires creating a new volume, copying data, and swapping —
  always surface this as a higher-effort remediation.

- NEVER delete snapshots without confirming the operator understands the
  data retention implications. EBS snapshots are the primary backup
  mechanism — deleting them without a replacement (DLM, AWS Backup) leaves
  the volume unprotected.

- NEVER recommend Snapshot Archive for snapshots that might be needed for
  disaster recovery within 72 hours. Archive retrieval takes 24-72 hours;
  this latency is unacceptable for DR scenarios. Archive ONLY for
  compliance or long-term retention.

- NEVER recommend Fast Snapshot Restore (FSR) without confirming the use
  case justifies the $43.20/AZ/month per snapshot cost. FSR is justified
  ONLY for boot volumes in auto-scaling groups with strict warmup
  requirements. Using FSR for data volumes or rarely-launched instances
  is pure waste.

- NEVER enable io2 multi-attach without confirming the workload uses a
  cluster-aware file system (OCFS2, GFS2, Oracle RAC). Concurrent
  uncoordinated writes to a multi-attached volume WILL corrupt data.

- NEVER assume st1 or sc1 can be used as boot volumes. Both are HDD-based
  and CANNOT serve as boot devices — only SSD types (gp2, gp3, io1, io2)
  support boot.

- NEVER modify a volume without first creating a pre-modification
  snapshot. While volume modification is online and low-risk, the snapshot
  provides a rollback path if the new configuration causes unexpected
  performance issues.

- NEVER stack multiple volume modifications in a single step. AWS allows
  only one pending modification per volume. Complete the current
  modification before starting the next.

- NEVER trust a single day of IOPS data for type migration decisions.
  I/O patterns vary by day-of-week and time-of-day. Require minimum 14
  days, preferably 30 days, of observation.

- NEVER recommend migrating from st1/sc1 to gp3 for workloads that are
  genuinely sequential (data warehouse, log processing). st1 is 44%
  cheaper than gp3 and better suited for high-throughput sequential I/O.

- NEVER ignore the instance type when evaluating io2 Block Express. Block
  Express requires Nitro-based instances (m5+, c5+, r5+). Recommending
  Block Express on a legacy instance (m4, c4) is a hard error.

- NEVER recommend FSR across AZs that don't launch instances from the
  snapshot. FSR charges per-AZ — if only us-east-1a launches instances,
  FSR in us-east-1b and us-east-1c is 100% waste.

- NEVER assume snapshot count is small. Always run
  `describe-snapshots --owner-ids self` to get the full count before
  assessing snapshot cost. Organizations with no DLM policy routinely
  accumulate 100-500+ snapshots per volume.

- NEVER batch-modify more than 5 volumes in a single output block. Volume
  modification can cause brief performance variations during the
  transition; a single systematic misclassification cascades into mass
  performance degradation. Apply in batches of 5, verify each batch.

- NEVER recommend gp3 with provisioned IOPS > 3000 without verifying
  `VolumeConsumedReadWriteOps` justifies the extra spend. The baseline
  3000 IOPS is free; anything above costs $0.005/IOPS-month. Only
  provision more if observed IOPS consistently exceeds 2500 (83% of
  baseline).

- NEVER forget to check for FSR when assessing snapshot cost. FSR can
  cost more than the snapshots themselves ($43.20/AZ/month vs $0.05/GB-
  month). An FSR-enabled snapshot on a 100 GB volume costs $43.20/month
  in FSR + $5.00/month in snapshot storage — FSR is 8.6× the snapshot cost.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`modify-volume`, `create-snapshot`, `modify-snapshot-tier`,
  `delete-snapshot`, `create-lifecycle-policy`), emit and await operator
  approval. Do NOT execute the CLI until the operator confirms.

- **Pre-modification snapshot.** Always capture a snapshot before
  modifying a volume:
  `aws ec2 create-snapshot --volume-id <id> --description "pre-<action>-<timestamp>"`.
  This provides a rollback path.

- **Verify no pending modifications.** Before starting a new modification:
  `aws ec2 describe-volumes-modifications --volume-ids <id>`. If
  `ModificationState != completed`, wait before starting a new one.

- **Volume modification is online but may cause brief performance
  variations.** Warn the operator that the transition period (up to 6
  hours) may see minor latency variation.

- **Snapshot deletion is irreversible.** Always confirm the operator
  understands that deleted snapshots cannot be recovered (unless archived
  to Snapshot Archive first).

- **DLM policy creation affects all matching volumes.** A DLM policy with
  `TargetTags` applies to all volumes with those tags, not just the
  target volume. Surface this scope in the CONFIRMATION gate.

- **FSR removal means the next launch from this snapshot will have cold-
  start latency.** Removing FSR saves money but restores cold-start
  behavior for instances launched from the snapshot. Verify the workload
  tolerates this.

- **Bulk-operation safety limit.** Remediation across a fleet MUST follow:
  1. Sort flagged volumes by estimated savings (largest first).
  2. Slice into batches of at most 5 volumes.
  3. For each batch: emit per-volume MIGRATION_STEPS, then a single
     CONFIRM for the batch.
  4. Verify each batch before proceeding to the next.
  5. Abort the sweep if any volume shows degraded `VolumeQueueLength`
     post-change.

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

## Recent AWS features (2024-2026)

- **gp3 general availability (mature):** gp3 is now the recommended
  default for most workloads. 20% cheaper than gp2 with baseline 3000
  IOPS + 125 MB/s. Migrate all gp2 volumes unless there is a documented
  reason not to.

- **io2 Block Express (expanded):** Up to 256,000 IOPS and 4,000 MB/s.
  Available on all Nitro-based instances. The right choice for extreme
  OLTP (Oracle RAC, SAP HANA) that cannot use gp3.

- **Snapshot Archive (GA):** 75% cheaper than standard snapshot storage
  ($0.0125 vs $0.05/GB-month). Retrieval takes 24-72 hours. Use for
  compliance archives and long-term retention where instant retrieval is
  not required.

- **Fast Snapshot Restore (FSR) visibility (2024-2025):** Enhanced
  CloudWatch metrics for FSR-enabled snapshots. Always check FSR cost
  during snapshot audits — it is the most expensive EBS feature per unit.

- **EBS volume modification speed (2024-2025):** Most type/IOPS/throughput
  modifications now complete within 6 hours (previously up to 24 hours).
  Size increases are typically instant. No downtime during modification.

- **gp3 IOPS and throughput increases:** gp3 now supports up to 16,000
  IOPS (up from 12,000 at launch) and 1,000 MB/s (up from 250 MB/s). This
  expands the gp3-eligible workload range — volumes that previously
  required io1 for 12,000-16,000 IOPS can now use gp3 at lower cost.

- **AWS Backup integration with EBS (2024-2025):** AWS Backup now
  provides cross-region and cross-account backup for EBS volumes with
  centralized governance. Use as an alternative to DLM for organizations
  with multi-service backup strategies.

## Error handling — procedure-level optimization failures

These branches complement the CLI/data-source table above. Each entry
describes what to do when an optimisation step itself fails — not when
a CLI call errors, but when the migration *cannot proceed safely*.

- **If `modify-volume` fails with `VolumeModificationRateExceeded`:**
  The account has exceeded the volume-modification throughput quota
  (default 500 modifications per account per region rolling window, with
  additional caps per-volume-type). Detection:
  `aws ec2 describe-volumes-modifications --filters Name=volume-id,
  Values=<id>` shows the prior modification still `modifying`. Do NOT
  retry immediately — retries count against the same quota. Remediation:
  (a) queue the modification with exponential backoff (start 60s, max
  600s); (b) for fleet migrations, sequence modifications with at least
  60s spacing and batch by ≤50 volumes per window; (c) request a quota
  increase via `service-quotas request-service-quota-increase
  --service-code ebs --quota-code L-<ID>`. Surface as `VERDICT:
  RATE_LIMITED` with retry-after and queue depth.

- **If gp2→gp3 migration is blocked because the attached instance type
  does not support gp3 (older generation, e.g., t2.micro, m1.small):**
  Detection: `aws ec2 describe-volume-status --volume-ids <id>` returns
  no error but the `modify-volume` API call returns
  `UnsupportedVolumeType`. The instance itself does not gate gp3 — but
  Nitro-only instance types gate certain IOPS/throughput ceilings.
  Remediation: (a) check the instance family in
  `aws ec2 describe-instances`; (b) for non-Nitro instances, the gp3
  baseline (3000 IOPS / 125 MB/s) still works but gp3's higher tiers
  (up to 16000 IOPS) require a Nitro instance; (c) if the workload
  needs the higher tier, plan an instance family migration BEFORE the
  volume migration. Do NOT migrate to gp3 with IOPS > 3000 on a
  non-Nitro instance — the IOPS will silently cap.

- **If io1→gp3 migration changes IOPS characteristics in a way the
  workload cannot tolerate:** io1 provides dedicated IOPS with strict
  latency guarantees; gp3 uses a credit-bucket model where sustained
  burst IOPS can be throttled after the burst credit is exhausted.
  Detection: before migration, check CloudWatch `VolumeConsumedReadWriteOps` against the io1 provisioned IOPS — if the p99
  exceeds the gp3 baseline (3000) for > 5 minutes per day, gp3 may
  throttle. Remediation: provision gp3 with explicit IOPS >= io1
  provisioned IOPS (up to 16000), OR keep io1/io2 for that volume.
  Surface as `VERDICT: IOPS_DEGRADE_RISK` with the p99 vs gp3 baseline
  delta and the gp3 provisioned-IOPS cost differential.

- **If the volume is in `error` or `in-use` state that blocks
  modification:** A volume in `error` state cannot be modified — it
  must be snapshotted and recreated. Detection:
  `aws ec2 describe-volumes --volume-ids <id> --query
  'Volumes[].State'`. Remediation: (a) for `error` state, create a
  snapshot (`create-snapshot`), create a new gp3 volume from the
  snapshot, detach the old volume (`detach-volume`), attach the new
  one (`attach-volume`); this requires an instance stop for the
  detach/attach window. (b) For `in-use` blocking modifications, note
  that gp2→gp3 type changes are live (no stop required) but
  size+type+IOPS changes together may require stop on some instance
  families — check the modification matrix in AWS docs.

- **If the instance cannot be stopped (production-critical, no
  maintenance window, no ASG):** Some migrations require instance stop
  (e.g., certain instance-family-gated IOPS, or re-attaching a restored
  volume). Remediation: defer the migration until a maintenance window
  OR migrate via a blue/green pattern (snapshot → new volume → attach
  to a replacement instance behind an ALB → shift traffic). Surface as
  `VERDICT: STOP_BLOCKED — schedule maintenance window or use blue/
  green replacement`.

## Edge cases

- **Multi-Attach volumes (io2 only) — cannot migrate to gp3.** EBS
  Multi-Attach is supported ONLY on io2 (and io2 Block Express) volume
  type. A gp3 migration silently breaks Multi-Attach because gp3 does
  not support it. Detection:
  `aws ec2 describe-volumes --volume-ids <id> --query
  'Volumes[].MultiAttachEnabled'`. Remediation: skip the migration and
  surface as a finding: `MULTI_ATTACH_BLOCKED — keep io2; gp3 does not
  support Multi-Attach`. If cost is the primary concern, evaluate
  whether the workload truly needs Multi-Attach (e.g., POSIX-compliant
  clustered filesystem) or whether it can be redesigned to use EFS or
  a shared data layer.

- **Volume attached to a Spot Instance that may be terminated
  mid-migration.** `modify-volume` is asynchronous; if the Spot
  Instance is reclaimed during the modification window, the volume
  state may transiently show `modifying` after detachment. Detection:
  `aws ec2 describe-spot-instance-requests`. Remediation: pause
  optimisation for Spot-attached volumes; the volume persists past
  instance termination and can be migrated when re-attached to a new
  instance. Do NOT attempt to migrate detached volumes that are
  pending re-attachment — the migration may complete but the new
  instance may expect the original type.

- **Volumes with Fast Snapshot Restore (FSR) enabled.** Migrating a
  volume with FSR does not propagate the FSR state — the new volume's
  snapshots need FSR enabled separately. Detection:
  `aws ec2 describe-fast-snapshot-restores`. Remediation: after
  migration, re-enable FSR on snapshots of the new volume; surface as
  `FOLLOWUP: re-enable FSR on snapshot <snap-id> in AZ <az>`.

## Domain

AWS CloudOps / EBS Block Storage Cost Optimization & FinOps.

## AWS documentation

- **Amazon EBS User Guide** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AmazonEBS.html
- **Amazon EBS volume types** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html
- **Amazon EBS pricing** — https://aws.amazon.com/ebs/pricing/
- **EBS volume modification** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/modify-volume.html
- **EBS snapshots** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EBSSnapshots.html
- **Snapshot Archive** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snapshot-archive.html
- **Fast Snapshot Restore** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-fast-snapshot-restore.html
- **io2 Block Express** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html#io2-block-express
- **EBS multi-attach** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volumes-multi.html
- **Amazon Data Lifecycle Manager** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snapshot-lifecycle.html
- **AWS Backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html
- **AWS CLI EC2 reference** — https://docs.aws.amazon.com/cli/latest/reference/ec2/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
