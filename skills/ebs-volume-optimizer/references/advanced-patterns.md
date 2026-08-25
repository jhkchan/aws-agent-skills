# Advanced Patterns (load on demand) — EBS Volume Optimizer

Step-0 expert behaviors, edge cases, deep-dive guidance, and 2024-2026 feature changes, moved verbatim from SKILL.md.


---

## Mindset — price-performance framing (moved from SKILL.md)

EBS cost optimization is a price-performance decision driven by observed
I/O patterns, not by provisioned specs. The goal is the cheapest volume
type and size that comfortably handles peak IOPS and throughput without
queue-length regression — not the absolute minimum that satisfies the
average. A type migration that triples `VolumeQueueLength` costs more in
application latency than it saves in EBS dollars. The decision framework
below favours conservatism: validate I/O headroom before migrating, and
always provide a rollback path via a pre-modification snapshot.

---

## Philosophy — four behaviours of a senior storage FinOps engineer (moved from SKILL.md)

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

---

## Step 0: Non-obvious behaviours that change the recommendation (moved from SKILL.md)

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

---

## Step 3: io2 Block Express evaluation (moved from SKILL.md)

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

---

## Verdict consistency rules (moved from SKILL.md)

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

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

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

---

## Edge cases (moved from SKILL.md)

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
