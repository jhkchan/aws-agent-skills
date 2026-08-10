# Example usage: ebs-volume-optimizer

A walkthrough showing the skill optimizing an over-provisioned io1
database volume, demonstrating the type migration decision (io1 to gp3),
the IOPS right-sizing math (consumed vs provisioned), the dollar savings
calculation, and the staged migration with a pre-modification snapshot.

## Input (user prompt)

> Review this EBS volume before our Q3 FinOps review. It's an io1 volume
> attached to our primary database and I suspect we're over-provisioned
> on IOPS.

```text
VolumeId: vol-prod-db-01
VolumeType: io1
Size: 1000 GB
Region: us-east-1
IOPS: 20000 (provisioned)
Attached instance: i-prod-db-primary (r5.2xlarge, PostgreSQL primary)

Metrics (last 30 days):
  - VolumeConsumedReadWriteOps: avg 2800/s, max 4500/s
  - VolumeQueueLength: avg 0.15, max 0.4
  - VolumeReadBytes + VolumeWriteBytes: avg 22 MB/s, max 38 MB/s

Snapshot policy: DLM with 7-day retention (snapshots governed)
FSR: not enabled

Workload context: PostgreSQL primary on r5.2xlarge (Nitro-based).
I/O is significant but well below the 20000 provisioned IOPS.
```

## Skill output

```text
TARGET: vol-prod-db-01
VERDICT: OPPORTUNITY_FOUND
REASON: io1 1000 GB volume with 20000 provisioned IOPS is consuming only
  avg 2800 IOPS (14% utilization), max 4500 IOPS (23% utilization).
  Migrating to gp3 with baseline 3000 IOPS provides insufficient headroom
  (only 0.67x of max consumed). However, gp3 with 6000 provisioned IOPS
  provides 1.33x headroom over max consumed — still 87% cheaper than io1
  at 20000 IOPS. gp3 IOPS cap is 16000, well above the 6000 needed
  (Step 1 + Step 3).
RECOMMENDATION:
  Current: io1, 1000 GB, 20000 provisioned IOPS
  Proposed: gp3, 1000 GB, 6000 IOPS (3000 baseline + 3000 extra)
  Dimensions changed: type (Step 1) + IOPS (Step 3)
  Confidence: HIGH — VolumeConsumedReadWriteOps avg 2800, max 4500 over
    30 days. gp3 6000 IOPS provides 1.33x headroom. Attached r5.2xlarge
    is Nitro-based (supports gp3 and io2 Block Express). DLM policy is
    active (snapshot dimension OK).
ESTIMATED_SAVINGS:
  Current monthly: $1,625.00
    storage: 1000 GB × $0.125 = $125.00
    IOPS: 20000 × $0.065 = $1,300.00
  Projected monthly: $95.00
    storage: 1000 GB × $0.08 = $80.00
    IOPS: (6000 - 3000 baseline) × $0.005 = $15.00
  Monthly saving: $1,530.00 (94% reduction)
  Annual saving: $18,360.00
  Assumptions: us-east-1 pricing, gp3 6000 IOPS covers max consumed
    (4500) with 33% headroom. VolumeQueueLength stable (< 1) confirms
    no IOPS bottleneck at this provisioned level.
MIGRATION_STEPS:
  1. Create a pre-modification snapshot:
     aws ec2 create-snapshot --volume-id vol-prod-db-01
       --description "pre-io1-to-gp3-migration-$(date +%s)"
       --tag-specifications "ResourceType=snapshot,Tags=[{Key=Name,
       Value=pre-gp3-db-01}]"
  2. Modify the volume type and IOPS in one step:
     aws ec2 modify-volume --volume-id vol-prod-db-01
       --volume-type gp3 --iops 6000
  3. Wait for modification to complete (check state):
     aws ec2 describe-volumes-modifications --volume-ids vol-prod-db-01
       --output json | jq '.VolumesModifications[] |
         {ModificationState, TargetVolumeType, TargetIops, Progress}'
     (State should reach "completed" within 6 hours)
  4. Verify IOPS and throughput:
     aws ec2 describe-volumes --volume-ids vol-prod-db-01 --output json
       | jq '.Volumes[] | {VolumeType, Iops, Throughput}'
  5. Monitor VolumeQueueLength and application performance for 7 days
     post-change:
     aws cloudwatch get-metric-statistics --namespace AWS/EBS
       --metric-name VolumeQueueLength
       --dimensions Name=VolumeId,Value=vol-prod-db-01
       --start-time $(date -d '-7 days' +%FT%TZ)
       --end-time $(date +%FT%TZ) --period 300
       --statistics Average,Maximum --output json
CONFIRM: Before modifying, emit and await:
  "CONFIRM: About to modify-volume vol-prod-db-01 (io1 20000 IOPS →
   gp3 6000 IOPS). Saving $1,530.00/month (94%). Online modification —
   no downtime. Rollback: pre-modification snapshot. Proceed? (yes/no)"
  Do NOT run the CLI until the operator confirms.
```

## What the skill caught that a generic assistant misses

1. **Consumed-vs-provisioned IOPS math.** A generic assistant says "you
   have too many IOPS, reduce them." The skill cites the exact consumed
   average (2800) and max (4500), computes the headroom ratio at the
   proposed setting (6000 / 4500 = 1.33x), and confirms gp3 baseline +
   extra is sufficient. It avoids the trap of recommending 3000 baseline
   IOPS when max consumed is 4500 (which would cause performance
   degradation).

2. **gp3 IOPS cap awareness.** The skill checks that the required IOPS
   (6000) is below the gp3 cap (16000). If max consumed had been 18000,
   the skill would have recommended staying on io2 (Block Express)
   instead of migrating to an insufficient gp3 configuration.

3. **Type migration + IOPS right-sizing in one step.** The skill stacks
   two savings dimensions (type migration from io1 to gp3 + IOPS right-
   sizing from 20000 to 6000) into a single `modify-volume` call. A
   generic assistant recommends only one dimension.

4. **Pre-modification snapshot for rollback.** The skill creates a
   snapshot before modifying. If the new configuration causes
   VolumeQueueLength spikes, the operator can restore from the snapshot.
   A generic assistant goes straight to `modify-volume` with no rollback
   path.

5. **DLM snapshot dimension is verified, not assumed.** The skill confirms
   the DLM policy is active (7-day retention) before declaring the
   snapshot dimension "OK." A generic assistant ignores the snapshot
   dimension entirely.

6. **Nitro instance check.** The skill confirms the attached r5.2xlarge
   is Nitro-based (required for gp3 advanced features and io2 Block
   Express). A generic assistant does not verify instance compatibility.

## Slash-command invocation

```
/aws:optimize-ebs-volume
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our EBS volumes for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: ebs-volume-optimizer]` and hands off
to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm the new volume type and IOPS landed
aws ec2 describe-volumes --volume-ids vol-prod-db-01 \
  --profile default --output json | \
  jq '.Volumes[] | {VolumeType, Iops, Throughput}'

# Monitor VolumeQueueLength for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/EBS \
  --metric-name VolumeQueueLength \
  --dimensions Name=VolumeId,Value=vol-prod-db-01 \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# Monitor consumed IOPS to verify headroom
aws cloudwatch get-metric-statistics --namespace AWS/EBS \
  --metric-name VolumeConsumedReadWriteOps \
  --dimensions Name=VolumeId,Value=vol-prod-db-01 \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json
```

If VolumeQueueLength sustains > 1.0 for more than 1 hour/day, the IOPS
provisioning is insufficient. Increase gp3 IOPS by 50% (6000 → 9000) or
consider migrating back to io2 with right-sized IOPS.

## Fleet-wide extension

For a fleet of N EBS volumes, run the skill in batch mode:

1. Identify all volumes with `aws ec2 describe-volumes`.
2. Filter by volume type:
   - gp2 → gp3 migration candidates (highest priority, 20% saving).
   - io1/io2 → gp3 migration candidates (check consumed IOPS first).
3. Sort by estimated monthly savings (largest first).
4. Slice into batches of 5 volumes.
5. For each batch: emit per-volume MIGRATION_STEPS, then a single CONFIRM
   for the batch.
6. Verify each batch (VolumeQueueLength stable) before proceeding to the
   next.
7. After the type-migration sweep, evaluate the snapshot dimension across
   all volumes (DLM policy gaps, Snapshot Archive opportunities, FSR waste).
