---
description: Optimise EBS volume cost through type migration (gp2 to gp3, io1/io2 to gp3), capacity right-sizing, IOPS/throughput tuning, snapshot governance (DLM, AWS Backup, Snapshot Archive), FSR removal, and io2 multi-attach consolidation with monthly savings estimates.
nl_triggers:
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
routes_to: ebs-volume-optimizer
---

# /aws:optimize-ebs-volume

Activate the `ebs-volume-optimizer` skill and optimize an EBS volume's cost
configuration across six dimensions: volume type, capacity, IOPS,
throughput, snapshot governance, and multi-attach.

## What it does

Reads a volume's CloudWatch metrics (VolumeReadOps, VolumeWriteOps,
VolumeQueueLength, VolumeConsumedReadWriteOps, BurstBalance), volume
configuration (type, size, IOPS, throughput), snapshot inventory, DLM/
AWS Backup policies, and FSR configuration, then applies the ordered
optimization logic:

1. **Pre-flight** — data sufficiency gate. If VolumeQueueLength metrics
   are absent, emits NEED_MORE_INFO. If the volume is detached, surface
   as a deletion candidate or NEED_MORE_INFO.
2. **Volume type migration** — gp2 to gp3 (20% cheaper, better baseline
   IOPS); io1/io2 to gp3 (when consumed IOPS < 50% of provisioned);
   io1 to io2 (same price, better durability); st1/sc1 for sequential and
   cold workloads.
3. **Capacity right-sizing** — downsize volumes where actual data << size.
   Note: size decrease requires new-volume + data-copy, not standard API.
4. **IOPS/throughput optimization** — gp3 baseline 3000 IOPS + 125 MB/s
   free; reduce over-provisioned IOPS on gp3 and io1/io2.
5. **Snapshot optimization** — create DLM/AWS Backup retention policy;
   archive old snapshots (75% cheaper); remove FSR ($43.20/AZ/month waste).
6. **Multi-attach consolidation** — io2 only: consolidate shared volumes
   across up to 16 Nitro instances.
7. **Impact estimation** — monthly + annual savings, assumptions documented.
8. **Verdict** — OPPORTUNITY_FOUND (any dimension has a recommendation),
   OPTIMIZED (applied and verified this session), or ALREADY_OPTIMAL.

Emits a deterministic optimization block per volume:

```text
TARGET: <volume-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <type> <size>GB, <IOPS> IOPS, <throughput> MB/s in <region>
  Proposed: <type> <size>GB, <IOPS> IOPS, <throughput> MB/s in <region>
  Dimensions changed: <type | capacity | iops | throughput | snapshot | fsr | multi-attach>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste an EBS volume's configuration and metrics and ask any of:

- "optimise this EBS volume's cost"
- "should I migrate from gp2 to gp3?"
- "are my provisioned IOPS right-sized?"
- "how much would Snapshot Archive save me?"
- "is Fast Snapshot Restore worth it?"
- "why is my snapshot bill so high?"
- "should I use multi-attach for this io2 volume?"
- "EBS fleet cost optimization review"

A bare volume ID + any optimization verb ("optimize this volume", "cost
review") also routes here via the orchestrator.

## Inputs

- Volume metadata: VolumeId, VolumeType, Size, IOPS, Throughput, region,
  attached instance.
- CloudWatch metrics (last 14-30 days):
  - `VolumeReadOps`, `VolumeWriteOps` (Average, Maximum, Sum)
  - `VolumeQueueLength` (Average, Maximum — the key performance signal)
  - `VolumeConsumedReadWriteOps` (for io1/io2 and gp3 with extra IOPS)
  - `BurstBalance` (for gp2 volumes — burst credit health)
  - `VolumeReadBytes`, `VolumeWriteBytes` (throughput utilization)
- Snapshot inventory: count, total size, age distribution, DLM/AWS Backup
  policy status.
- FSR configuration: enabled AZs, snapshot IDs.
- Optional: workload context (database type, I/O pattern, latency SLO)
  for type-selection decisions.

## Outputs

- One optimization block per volume.
- Confidence level with rationale (HIGH requires VolumeQueueLength data +
  VolumeConsumedReadWriteOps cross-check).
- Estimated monthly and annual savings, broken down by dimension.
- Specific migration steps with CLI commands (modify-volume,
  create-snapshot, create-lifecycle-policy, modify-snapshot-tier,
  disable-fast-snapshot-restores).
- Pre-modification snapshot for rollback safety.
- VolumeQueueLength monitoring guidance for 7 days post-change.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for EBS block storage cost).
- `/aws:optimize-ec2-rightsizing` for EC2 instance rightsizing (the
  compute counterpart; pairs with EBS optimization for full instance
  cost review).
- `/aws:optimize-s3-lifecycle` for object storage cost optimization (S3
  and EBS are typically the two largest storage lines in an AWS bill).
- `/aws:audit-ebs-volume` for EBS security/configuration audit (encryption,
  attachment status, public snapshot exposure — not cost optimization).
