# Advanced Patterns (load on demand) — EC2 Backup Operator

Step-0 expert behaviors, edge cases, deep-dive guidance, and 2024-2026 feature changes, moved verbatim from SKILL.md.


---

## Quick reference: Cost/time baselines (2026) (moved from SKILL.md)

**Cost/time baselines (2026):**

- EBS snapshot create: ~1 min per 100 GB (storage-bound); first snapshot
  is full, subsequent snapshots of the same volume are incremental (block-
  level diff).
- Cross-region snapshot copy: $0.02/GB transfer + destination-region
  storage ($0.05/GB-mo standard, $0.0125/GB-mo archive tier).
- AMI create: same as snapshot create for each attached EBS volume, plus
  metadata registration (~seconds).
- AWS Backup restore job: minutes to hours depending on size; PITR for EC2
  continuous backups supports 1-second-granularity restore for the last 35
  days.
- FSR cost: $0.06/hr per AZ per snapshot (~$43.20/AZ-month) — verify the
  latency benefit justifies the cost.
- Vault lock: free; the cost is the immutability commitment (you cannot
  delete backups before the retention expires).

---

## Mindset — three EC2 backup realities (moved from SKILL.md)

- **Snapshots are incremental but the chain is independent of snapshot-id
  ordering.** EBS tracks blocks by reference count. Deleting an intermediate
  snapshot migrates its unique blocks to later snapshots that reference
  them — storage is freed only when a block is unreferenced by ANY
  remaining snapshot. The delete is safe but the cost saving may lag by
  weeks. A `delete-snapshot` of the "oldest" snapshot does NOT cascade
  forward.
- **`deregister-image` does NOT delete the AMI's snapshots.** Deregister
  removes the AMI metadata; the underlying EBS snapshots persist and
  continue to bill until explicitly deleted. Conversely, `delete-snapshot`
  of a snapshot referenced by a registered AMI bricks launches from that
  AMI (the volume can't be created). The full AMI cleanup is deregister +
  delete-snapshot per EBS-mapping snapshot.
- **Vault lock has two modes with different immutability.** Compliance mode
  is immutable for the entire retention period — NO role, including root,
  can delete or modify backups before expiry. Governance mode locks most
  users but `Backup:$account:full-access` roles can break retention —
  governance mode is a guardrail, not a WORM. A compliance auditor who
  assumes "vault-locked" means compliance-mode will be wrong half the time.

---

## Step 0: Expert knowledge — non-obvious EC2/EBS backup behaviors (moved from SKILL.md)

These behaviors are easy to misjudge without operational EC2 backup
experience. Each changes a plan if ignored:

- **Snapshots are incremental but the chain is reference-counted, not
  ordered.** EBS stores unique blocks; each snapshot references the blocks
  it captured. Deleting any snapshot is safe — its unique blocks migrate
  to later snapshots that reference them. The cost saving from a delete
  may lag by weeks (until the blocks are unreferenced by ANY remaining
  snapshot). Never tell an operator "the storage cost drops immediately
  after delete."

- **`create-image` reboots the source by default.** Without `--no-reboot`,
  the instance is rebooted to quiesce filesystems for an app-consistent
  snapshot. Pass `--no-reboot` for a crash-consistent AMI (faster, no
  reboot, but the filesystem is captured mid-write — fsck on first boot
  is normal). For databases, either stop the DB engine before AMI create
  OR use `--no-reboot` and accept crash-consistency (most modern DBs
  recover cleanly).

- **`deregister-image` does NOT delete the AMI's snapshots.** Deregister
  removes only the metadata registration. The EBS snapshots in the AMI's
  `BlockDeviceMappings` continue to exist and bill. Full AMI cleanup is
  deregister, then `delete-snapshot` per EBS-mapping snapshot. Operators
  who "clean up old AMIs" by deregistering alone are paying for orphaned
  snapshots for years.

- **`delete-snapshot` of a snapshot referenced by a registered AMI fails
  OR bricks launches.** Newer API versions reject the delete with
  `InvalidSnapshot.InUse`; older API versions allow it and the AMI fails
  to launch. Always check `describe-images --filters
  BlockDeviceMapping.SnapshotId=<id>` before delete.

- **Cross-account encrypted snapshot share requires BOTH the snapshot
  attribute AND the source KMS key policy.** `modify-snapshot-attribute
  --create-volume-permission` shares the snapshot; the recipient can
  `describe-snapshots` but cannot `create-volume` or `copy-snapshot`
  without `kms:Decrypt` and `kms:CreateGrant` on the source's KMS key.
  Cross-region copy additionally requires the recipient to re-encrypt
  with their own KMS key in the destination region.

- **Cross-region snapshot copy re-encrypts with a destination-region KMS
  key.** The source-region KMS key cannot decrypt in the destination
  region (KMS keys are regional). The copy operation must specify
  `--kms-key-id` in the destination region; passing the source key ARN
  fails.

- **Snapshot Archive tier restore takes 24-72 hours.** Tiered snapshots
  cost $0.0125/GB-mo (vs $0.05/GB-mo standard) but the restore latency is
  much higher. Use archive only for cold retention; for DR, keep a
  standard-tier copy in the DR region.

- **`describe-snapshots` without `--owner-ids self` returns EVERY public
  snapshot in the world.** This call is throttled and rate-limited.
  ALWAYS pass `--owner-ids self` (or an explicit owner ID) for inventory
  operations.

- **AMI launch permissions are separate from snapshot permissions.**
  Sharing an AMI with another account (`modify-image-attribute --launch-
  permission`) does NOT share the underlying snapshots — the recipient
  can launch but cannot `create-volume` from the AMI's snapshots
  directly. To enable direct snapshot use, also `modify-snapshot-
  attribute --create-volume-permission`.

- **`DeleteOnTermination: true` on the root volume of an AMI's launch is
  a data-loss vector.** If the launched instance is terminated, the root
  volume is deleted automatically. For stateful launches, set
  `BlockDeviceMappings[].Ebs.DeleteOnTermination=false` on launch.

- **AWS Backup vault lock in compliance mode is immutable.** Once the
  vault is locked in compliance mode AND the cool-down period passes,
  NO role (including root) can delete or modify backups before the
  retention expires. Set the retention carefully; you cannot shorten it
  later. Cooling-down period (default 72 hr) lets you back out.

- **AWS Backup governance mode is NOT WORM.** Governance mode locks most
  users but `Backup:$account:full-access`-equivalent roles can break
  retention. Compliance auditors must verify the mode, not just that the
  vault is "locked."

- **AWS Backup continuous backups enable 1-second-granularity PITR for
  EC2.** Set `BackupRule.BackupOptions.WindowsVSS: enabled` and
  `BackupRule.Lifecycle` with a continuous-backup vault. The 35-day
  window is the maximum; shorter windows reduce cost. Restore creates a
  new EC2 instance with new volume-ids.

- **DLM policy tags target resources; security groups / VPC are NOT in
  the policy.** DLM snapshots capture the volume only — they do NOT
  capture the instance metadata, security groups, or launch config. For
  instance-level restore, use AMI-based DLM (`PolicyType: IMAGE_MANAGEMENT`)
  or AWS Backup (which captures the entire EC2 resource).

- **`copy-snapshot` with `--source-region` and `--destination-region` is
  idempotent only by description-tag, not by snapshot-id.** Two copies
  of the same source snapshot produce two destination snapshots. Track
  source via the `Description` field or a `copied-from` tag.

- **FSR (Fast Snapshot Restore) bills per-AZ per-snapshot, regardless of
  use.** $0.06/hr per AZ per snapshot (~$43.20/AZ-month). Enable FSR only
  on snapshots that gate latency-sensitive launches; for routine DR,
  prefer standard tier (the first-volume-create is slow but the cost is
  zero ongoing).

- **`create-volume-from-snapshot` with a different AZ or KMS key is
  explicit.** Volume inherits snapshot's size and type unless
  overridden. To resize on restore, pass `--size`. To re-encrypt with a
  different key, pass `--encrypted --kms-key-id`. Cross-AZ volume
  creation is allowed but attach must be in the same AZ as the instance.

- **AWS Backup restore job for EC2 creates a NEW instance with NEW
  volume-ids and a NEW ENI.** The original instance is unchanged. The
  new instance may have a different private IP (if the original IP was
  released). Plan application connection-string cutover.

- **Snapshot tiering via DLM Archive rule is separate from the standard
  tier.** A DLM policy can have a `PolicyActions` with
  `SnapshotTiering` to archive snapshots after N days. The archive
  snapshot has the same id but a different `StorageTier`.

---

## Step 3: Execute behind CONFIRM gate (moved from SKILL.md)

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI, emit:
  `CONFIRM: About to <operation> on <instance/volume/snapshot/AMI/vault>
  in account <account> region <region>. This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.
- Capture pre-state for rollback: `aws ec2 describe-volumes --volume-ids
  <id> --output json > /tmp/<id>-pre-$(date +%s).json`. EBS state is not
  versioned.
- Execute the CLI. Capture the new resource id (snapshot-id, AMI-id,
  volume-id, instance-id, restore-job-id).
- For long-running operations, wait via `aws ec2 wait snapshot-completed`
  / `aws ec2 wait image-available` / `aws ec2 wait volume-available` /
  `aws ec2 wait instance-running` / `aws backup wait-restore-job-completed`.

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

## Recent AWS features (2024-2026)

- **AWS Backup for Amazon FSx (2024-2025):** AWS Backup now natively
  backs up FSx for Lustre, FSx for OpenZFS, and FSx for NetApp ONTAP.
  Operators should centralize FSx backups in the same vault as EC2/RDS
  for unified DR orchestration and vault lock coverage.

- **Fast Snapshot Restore (FSR) GA and cost transparency (2024):** FSR
  eliminates initialization latency on restored volumes. Operators must
  audit FSR usage — the $0.06/hr per-AZ cost routinely exceeds storage
  cost 10-30x. Use only for snapshots gating latency-sensitive launches.

- **Snapshot Archive tier (2024-2025):** `modify-snapshot-tier` or DLM
  `SnapshotTiering` rule moves snapshots to the $0.0125/GB-mo archive
  tier. 24-72 hr restore latency. Apply the 180-day staleness threshold
  (vs 90-day for standard tier) when auditing.

- **EBS Snapshots Recycling Bin (2024):** The Recycling Bin retains
  deleted snapshots for a configurable period (1-365 days) for recovery
  from accidental deletes. Operators should set a Recycling Bin rule
  alongside any deletion automation.

- **AWS Backup Vault Lock cool-down (2024-2025):** Vault lock has a
  configurable cool-down period (`ChangeableForDays`, default 72 hr)
  during which compliance-mode lock can be backed out. After cool-down,
  compliance mode is irreversible. Operators must surface the cool-down
  state in every vault-lock plan.

- **AWS Backup continuous backups for EC2 (2024):** Continuous backups
  enable 1-second-granularity PITR for EC2 (35-day window). Requires a
  continuous-backup vault and a BackupRule with `BackupOptions`. The
  restore creates a new EC2 instance at the specified timestamp.

- **DLM IMAGE_MANAGEMENT GA (2024):** DLM now supports AMI lifecycle
  policies (not just snapshots), enabling automated AMI creation and
  deregistration. Operators can use a single DLM policy for AMI-based
  instance-level backups.

- **EC2 Image Builder integration with AMI lifecycle (2024-2025):**
  Image Builder pipelines now emit `DeprecationTime` on produced AMIs
  automatically. Operators should verify that launch templates skip
  deprecated AMIs.

- **Cross-account AWS Backup (2025):** AWS Backup now supports cross-
  account backup management via AWS Organizations, simplifying the KMS
  key policy coordination that previously made cross-account EC2
  restore error-prone.
