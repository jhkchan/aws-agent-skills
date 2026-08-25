---
name: ebs-volume-optimizer
description: 'Optimises EBS volume cost across six dimensions: volume type migration (gp2 to gp3 is 20% cheaper with higher baseline IOPS; io1/io2 to gp3 when provisioned IOPS are unused; st1/sc1 for sequential and cold workloads), capacity right-sizing (downsize volumes where actual data is much smaller than provisioned), IOPS/throughput optimization (gp3 baseline 3000 IOPS + 125 MB/s free; detect over-provisioned io1/io2), snapshot hygiene (automate deletion via DLM/AWS Backup; Snapshot Archive is 75% cheaper; FSR is expensive and only for boot volumes), io2 multi-attach consolidation, and impact estimation with dollar savings. Emits OPPORTUNITY_FOUND with specific recommendation and estimated savings, OPTIMIZED, or ALREADY_OPTIMAL. Use when reviewing EBS spend, planning a gp2-to-gp3 migration sweep, auditing snapshot accumulation, or building a storage FinOps savings plan.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted volume configuration and CloudWatch metrics. Live-account optimization uses aws ec2 describe-volumes, aws ec2 describe-volume-attribute, aws ec2 describe-volumes-modifications, aws cloudwatch get-metric-statistics (VolumeReadBytes, VolumeWriteBytes, VolumeReadOps, VolumeWriteOps, VolumeQueueLength, VolumeThroughputPercentage, VolumeConsumedReadWriteOps)...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Optimising EBS volume cost, planning a gp2-to-gp3 migration sweep, auditing snapshot accumulation, right-sizing volume capacity, tuning provisioned IOPS on io1/io2 volumes, evaluating Snapshot Archive or Fast Snapshot Restore, consolidating volumes via io2 multi-attach, or building a storage FinOps savings plan.
  when_not_to_use: S3 storage cost (use s3-lifecycle-optimizer), EC2 instance rightsizing (use ec2-rightsizing-optimizer), Lambda cost (use lambda-cost-optimizer), or EBS performance troubleshooting (use the EC2/EBS troubleshooter). This skill focuses on cost-driven volume optimization decisions, not performance debugging.
  activation_triggers: optimise EBS volume cost, gp2 to gp3 migration, EBS volume right-sizing, EBS snapshot cleanup, provisioned IOPS unused, io1 to gp3 migration, EBS Snapshot Archive, Fast Snapshot Restore cost, EBS multi-attach consolidation, EBS burst credits exhausted, VolumeQueueLength high, EBS FinOps savings, EBS monthly savings estimate, reduce EBS bill, storage cost review
  invocation_schema: 'Input: either (a) a volume identifier + live-account context, (b) a volume configuration document (volume type, size, IOPS, throughput, attached instance), OR (c) CloudWatch EBS metrics (VolumeReadBytes, VolumeWriteBytes, VolumeReadOps, VolumeWriteOps, VolumeQueueLength) with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS block per volume, where VERDICT is one of OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL.'
  invocation_example: "# Minimal valid input (offline finding classification):\nVolumeId: vol-0abc123\nVolumeType: gp2\nSize: 500 GB\nRegion: us-east-1\nIOPS: 1500 (baseline for gp2 at this size)\nAttached instance: i-prod-db-01 (PostgreSQL primary)\nMetrics (last 30 days):\n  - VolumeReadOps + VolumeWriteOps: avg 250/s, max 400/s\n  - VolumeQueueLength: avg 0.2, max 0.8\n  - VolumeReadBytes + VolumeWriteBytes: avg 8 MB/s, max 15 MB/s\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EBS, gp3, gp2, io1, io2, st1, sc1, volume type migration, right-sizing, IOPS, throughput, provisioned IOPS, burst credits, snapshot, Snapshot Archive, Fast Snapshot Restore, FSR, DLM, AWS Backup, multi-attach, VolumeQueueLength, cost optimization, FinOps
  tags: ebs, storage, cost-optimization, finops, gp3, snapshot, right-sizing, volume-type
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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Philosophy

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

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

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Step 2: Capacity right-sizing

Volume size right-sizing identifies volumes where the provisioned capacity
is significantly larger than the actual data stored.

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

#### Right-sizing decision table

| Observation | Verdict | Action |
|---|---|---|
| Actual data < 50% of provisioned size | **OPPORTUNITY_FOUND** (downsize) | Create a new smaller volume, copy data, swap. Surface as higher-effort remediation. |
| Actual data 50-80% of provisioned size | MEDIUM — consider downsize at next maintenance | Not urgent; monitor growth trend. |
| Actual data > 80% of provisioned size | ALREADY_OPTIMAL (capacity) | Size is appropriate; do not downsize. |
| gp2 with BurstBalance chronically near 0 | **OPPORTUNITY_FOUND** (migrate to gp3) | gp2 burst credits exhausted — switch to gp3 for higher baseline IOPS. |

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Step 3: IOPS/throughput optimization

For gp3 and io1/io2 volumes, provisioned IOPS and throughput may be
over-spec'd relative to actual usage.

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

| Observation | Verdict | Action |
|---|---|---|
| gp3 with IOPS > 3000 AND VolumeConsumedReadWriteOps avg < 1500 (50% of baseline) | **OPPORTUNITY_FOUND** (reduce IOPS to baseline) | Set IOPS to 3000 (free baseline). Saving: `(current_IOPS - 3000) × $0.005`/month. |
| gp3 with Throughput > 125 AND observed throughput < 60 MB/s | **OPPORTUNITY_FOUND** (reduce throughput to baseline) | Set Throughput to 125 (free baseline). Saving: `(current_MBps - 125) × $0.04`/month. |
| io1/io2 with provisioned IOPS >> consumed | **OPPORTUNITY_FOUND** (reduce IOPS or migrate to gp3) | Reduce IOPS to consumed_max × 1.3, OR migrate to gp3 if consumed < 16,000. |

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

### Step 4: Snapshot optimization

Snapshots are a major cost line that accumulates silently.

Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

#### Snapshot optimization decision matrix

| Observation | Verdict | Action |
|---|---|---|
| Snapshots exist with no DLM or AWS Backup policy | **OPPORTUNITY_FOUND** (snapshot governance) | Create DLM policy with retention (e.g., keep 7 daily, 4 weekly). |
| Snapshots older than 90 days with no restore in 90 days | **OPPORTUNITY_FOUND** (Snapshot Archive) | Archive to save 75% ($0.0125 vs $0.05/GB-month). |
| FSR enabled on data volumes (not boot volumes) | **OPPORTUNITY_FOUND** (FSR removal) | Remove FSR — $43.20/AZ/month per snapshot. Only justified for boot volumes. |
| FSR enabled across multiple AZs but the volume is in one AZ | **OPPORTUNITY_FOUND** (FSR right-size) | Remove FSR from AZs that don't launch instances from this snapshot. |
| Daily snapshots with indefinite retention | **OPPORTUNITY_FOUND** (retention cap) | Set retention to 30-90 days; archive older snapshots. |

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Step 5: Multi-attach consolidation (io2 only)

If multiple EC2 instances in the same cluster each have their own io2
volume for shared data, they may be candidates for consolidation via io2
multi-attach.

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

**Multi-attach decision:**

| Observation | Verdict | Action |
|---|---|---|
| 2+ io2 volumes attached to instances in the same cluster with similar data | **OPPORTUNITY_FOUND** (consolidation) | Consolidate to one io2 volume with multi-attach. Saves N-1 volumes. |
| Cluster-aware file system (OCFS2, GFS2) in use | Multi-attach is safe | Proceed with consolidation. |
| No cluster-aware file system | Multi-attach is UNSAFE | Do NOT enable multi-attach without a cluster-aware file system — concurrent writes will corrupt data. |

### Step 6: Impact estimation

Compute the monthly savings for each recommendation:

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

Moved verbatim to [references/ebs-pricing-and-type-matrix.md](references/ebs-pricing-and-type-matrix.md) - load on demand (see References below).

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

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

## Verdict semantics — reconciling the verdict_shape

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one dimension has a concrete, savings-bearing recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | A change was applied and verified this session; metrics confirm the new config lands within healthy performance bands. | Primary — only emitted post-remediation. |
| `ALREADY_OPTIMAL` | All dimensions pass (volume on optimal type, capacity right-sized, IOPS within baseline, snapshots governed, no FSR waste). | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Data gate failed: VolumeQueueLength metrics absent, observation window < 14 days, or volume detached with no I/O history. | Pre-decision — emit before any recommendation. |
| `BLOCKED` | Volume `State = error` or `recovering`; IAM denies `ec2:DescribeVolumes`; or the volume is in a failed state. | Pre-decision — emit when no reliable signal exists. |

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).

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

Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

Moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand (see References below).

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Mindset/Philosophy framing, Step 0 non-obvious behaviours, io2 Block Express evaluation, verdict consistency rules, edge cases, and 2024-2026 feature changes moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight I/O-metric and snapshot-inventory commands, over-sized-volume detection, and snapshot audit commands moved from SKILL.md
- [references/error-handling.md](references/error-handling.md) — CLI/data-source failure tables and procedure-level optimization failure branches moved from SKILL.md
- [references/worked-examples.md](references/worked-examples.md) — gp2→gp3 and io1/io2→gp3 migration CLI patterns, DLM/archive/multi-attach patterns, impact-estimation formula, four secondary worked examples, and remediation guidance moved from SKILL.md
- [references/ebs-pricing-and-type-matrix.md](references/ebs-pricing-and-type-matrix.md) — us-east-1 pricing reference table moved from SKILL.md (extends the existing pricing/type matrix)

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
