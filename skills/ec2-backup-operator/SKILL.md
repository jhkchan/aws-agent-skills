---
name: ec2-backup-operator
description: >-
  Operates EC2 backup and snapshot workflows safely — EBS snapshot
  create and cross-region/cross-account copy, AMI creation and
  deregistration lifecycle, AWS Backup plans and vaults with vault
  lock, Data Lifecycle Manager (DLM) automated policies, point-in-
  time recovery for EC2, application-consistent vs crash-consistent
  snapshot verification, and full restore procedures. Runs
  deterministic pre-checks (instance state, volume attached,
  snapshot quota, KMS key policy for cross-account copy, AMI
  references for snapshot delete, FSR status, vault lock mode),
  executes the operation behind a CONFIRM gate, and emits a verdict
  (READY | BLOCKED | COMPLETED) per operation with the exact CLI
  sequence, expected side-effects, and post-verification. Use when
  creating a pre-migration AMI, scheduling a DLM policy, enabling
  AWS Backup vault lock, restoring a volume from a snapshot,
  launching from an AMI, or diagnosing a snapshot stuck in pending.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws ec2 create-snapshot, describe-snapshots, copy-snapshot,
  create-image, describe-images, deregister-image, delete-snapshot,
  create-volume, run-instances, modify-snapshot-tier, describe-fast-snapshot-
  restores; aws backup create-backup-plan, create-backup-vault,
  put-backup-vault-lock-config, start-backup-job, start-restore-job,
  describe-restore-job; aws dlm create-lifecycle-policy (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - EC2
  - EBS
  - EBS snapshot
  - AMI
  - create-image
  - create-snapshot
  - copy-snapshot
  - deregister-image
  - delete-snapshot
  - AWS Backup
  - backup plan
  - backup vault
  - vault lock
  - compliance mode
  - backup selection
  - Data Lifecycle Manager
  - DLM
  - lifecycle policy
  - point-in-time recovery
  - PITR
  - continuous backup
  - snapshot chain
  - incremental snapshot
  - Fast Snapshot Restore
  - FSR
  - snapshot archive
  - snapshot tiering
  - fsfreeze
  - application-consistent
  - crash-consistent
  - create-volume-from-snapshot
  - launch-from-AMI
  - cross-region copy
  - cross-account share
  - KMS key policy
  - snapshot attribute
tags: [ec2, ebs, ami, aws-backup, dlm, storage, backup, restore, snapshot, disaster-recovery, operate]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY | BLOCKED | COMPLETED"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags: [ec2, ebs, ami, aws-backup, dlm, storage, backup, restore, snapshot, disaster-recovery, operate]
  dependencies: [aws-orchestrator]
  keywords:
    - EC2
    - EBS
    - snapshot
    - AMI
    - AWS Backup
    - DLM
    - vault lock
    - Fast Snapshot Restore
  when_to_use: >-
    Creating a pre-migration AMI from a running or stopped EC2 instance,
    taking a manual EBS snapshot before a risky change, copying snapshots
    cross-region or cross-account, building or modifying an AWS Backup plan
    with vault lock (compliance mode), creating a DLM lifecycle policy for
    automated snapshot retention, restoring a volume from a snapshot,
    launching a new instance from an AMI, starting an AWS Backup restore
    job, diagnosing a snapshot stuck in pending, or enabling Fast Snapshot
    Restore for latency-sensitive restores.
  activation_triggers:
    - "create AMI from instance"
    - "create EBS snapshot"
    - "copy snapshot cross-region"
    - "share snapshot cross-account"
    - "deregister AMI"
    - "delete AMI snapshot"
    - "create AWS Backup plan"
    - "enable backup vault lock"
    - "create DLM lifecycle policy"
    - "restore volume from snapshot"
    - "launch instance from AMI"
    - "start AWS Backup restore job"
    - "snapshot stuck in pending"
    - "enable Fast Snapshot Restore"
    - "tier snapshot to archive"
    - "application-consistent snapshot"
  invocation_schema: >-
    Input: either (a) an EC2 backup/restore operation request
    (operation=create-snapshot | copy-snapshot | create-image |
    deregister-image | delete-snapshot | create-backup-plan |
    enable-vault-lock | create-dlm-policy | restore-volume |
    restore-from-ami | start-restore-job) paired with the target
    instance/volume/snapshot/AMI/plan-id, OR (b) the resource-id +
    operation for live-account execution. Output: deterministic
    OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation,
    where VERDICT is one of READY, BLOCKED, COMPLETED.
---

# EC2 Backup Operator

## What this skill does

Executes EC2 backup and snapshot operations correctly and safely across
EBS, AMI, AWS Backup, and Data Lifecycle Manager. Runs deterministic
pre-checks (instance state, volume attached, snapshot quota, KMS key
policy for cross-account copy, AMI references for snapshot delete),
plans the exact `aws ec2` / `aws backup` / `aws dlm` CLI sequence,
and verifies the result. Every state-changing operation runs behind a
CONFIRM gate — AMI creation reboots the source instance by default
unless `--no-reboot` is passed; snapshot delete is irreversible.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority order + tool-selection matrix | Before any operation |
| **§ Mindset** | Why pre-checks matter, the snapshot-chain surprise, the AMI-deregister trap | Understanding the safety model |
| **§ Pre-flight** | Resource metadata gate — instance, volume, snapshot, AMI, KMS, vault | Before executing any CLI |
| **§ Process** | Per-operation planning: snapshot, AMI, AWS Backup, DLM, restore | When choosing which operation to run |
| **§ Output format** | Structured VERDICT block with COMMANDS, NEW_RESOURCE, RESTORE_JOB | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that brick launches or lose data | Review before any delete |
| **§ Pre-flight safety** | CONFIRM gate, snapshot pre-state, vault lock planning, rollback | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (instance not in valid state, volume detached, snapshot in `error`/`pending`, AMI references the snapshot being deleted, KMS key policy missing for cross-account copy, vault lock in governance mode blocks the caller, snapshot quota exceeded, source region not opted-in) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator `yes` |
| `COMPLETED` | Operation finished and post-verification passed (snapshot `completed`, AMI `available`, restore job `COMPLETED`, volume `in-use` after attach) | Emit new resource IDs, verification results, follow-ups |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY):**

1. **Source resource state** — instance/volume/snapshot/AMI must be in a
   state that supports the operation. `pending`/`busy` snapshots, AMIs in
   transient states, and instances in `shutting-down`/`stopped` (for
   `--no-reboot`-false AMI create) BLOCK.
2. **IAM and KMS permissions** — caller needs the `ec2:*` / `backup:*` /
   `dlm:*` action; cross-account snapshot copy needs the source account's
   KMS key policy to grant the recipient `kms:Decrypt` AND the snapshot
   attribute to share the snapshot.
3. **Quota and limits** — manual snapshot quota per region (default 100,000
   but service-quota-controlled), AMI quota, FSR per-AZ quota (default 50
   FSN-enabled snapshots per region), AWS Backup vault lock min/max
   retention.
4. **Reference integrity** — deleting a snapshot referenced by an AMI or
   by FSR bricks launches. Always check `describe-images` BlockDeviceMappings
   and `describe-fast-snapshot-restores` before any `delete-snapshot`.
5. **Reboot tolerance** — `create-image` without `--no-reboot` reboots the
   source; `NoReboot=true` produces a crash-consistent AMI (acceptable for
   most stateless/state-tolerant workloads; risky for databases).
6. **Vault lock mode** — governance-mode vault lock lets the privileged
   operator break retention; compliance-mode vault lock does not. The
   pre-check surfaces the mode so the operator cannot accidentally rely on
   immutability that is not enforced.

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

## Tool-selection matrix — which service to use

| Goal | Best tool | Why |
|---|---|---|
| One-off snapshot of a single volume before a risky change | `aws ec2 create-snapshot` | Direct, no setup overhead |
| Cross-region DR copy of a snapshot | `aws ec2 copy-snapshot` | Native cross-region, re-encrypts with destination-region KMS |
| Cross-account snapshot share | `modify-snapshot-attribute` + KMS key policy | Native attribute + KMS grant |
| Bootable image of a running/stopped instance | `aws ec2 create-image` | Captures all attached volumes + metadata |
| Fleet-wide automated daily snapshots with retention | **Data Lifecycle Manager (DLM)** | Simplest, schedule-based, tags for targeting |
| Cross-service backup orchestration (EC2+RDS+EFS+FSx) | **AWS Backup** | Single plan, cross-region/cross-account copy, vault lock |
| Compliance-driven immutable backups (WORM) | **AWS Backup vault lock** | Only native WORM for EC2/EBS backups |
| Point-in-time recovery (PITR) for EC2 with 1-second granularity | **AWS Backup continuous backups** | Only native PITR for EC2 (35-day window) |
| Fast restore of a snapshot-backed volume into a latency-sensitive workload | **Fast Snapshot Restore (FSR)** | Pre-warms the volume to full IOPS on first read |
| Long-term low-cost snapshot retention (>90 days) | **Snapshot Archive tier** | $0.0125/GB-mo, 24-72 hr restore |
| Pre-migration capture of a complete instance | **AMI** | Single artifact with all volumes + launch permissions |

## Mindset

**One-line takeaway:** snapshots are incremental and chained; deleting an
AMI does NOT delete its snapshots; vault lock immutability depends on the
mode. Driven by three EC2 backup realities:

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

## Pre-flight: resource metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `describe-snapshots` paginates at 500/page — ALWAYS pass
`--owner-ids self` (without it, the call returns every public snapshot in
the world and is rate-limited). `describe-images` paginates at 200/page
when filtering by owner. AWS Backup jobs paginate at 100/page.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws ec2 describe-instances --instance-ids <id>` — confirm `State` is
   `running` or `stopped` for AMI create; capture `BlockDeviceMappings`
   (volume-ids), `IamInstanceProfile`, `RootDeviceName`, VPC/subnet/SG
   context (needed for launch-from-AMI restore).
2. `aws ec2 describe-volumes --volume-ids <id>` — confirm `State: in-use`
   for attached volumes, capture `Encrypted`, `KmsKeyId`, `Size`,
   `VolumeType`, `Iops`, `Throughput`, `Attachments` (AttachTime, DeleteOnTermination).
3. `aws ec2 describe-snapshots --snapshot-ids <id> --owner-ids self` —
   confirm `State: completed`; capture `StartTime` (age), `VolumeId`,
   `Encrypted`, `KmsKeyId`, `Description`, `Tags`, `StorageTier` (standard
   vs archive).
4. `aws ec2 describe-images --image-ids <id> --owners self` — confirm
   `State: available`; capture `BlockDeviceMappings` (the snapshot-ids
   backing the AMI), `RootDeviceType`, `DeprecationTime`, `Tags`.
5. `aws ec2 describe-snapshot-attribute --snapshot-id <id> --attribute
   createVolumePermission` — for cross-account share, verify whether
   `Group: all` (public) or specific account IDs are present.
6. `aws kms describe-key --key-id <kms-key-id>` — for encrypted snapshots,
   confirm `KeyState: Enabled` and the key policy grants the caller
   `kms:Decrypt` and `kms:CreateGrant`. For cross-account copy, the source
   account's KMS key policy MUST grant the recipient.
7. `aws ec2 describe-fast-snapshot-restores` — for any snapshot targeted
   for delete, verify it is NOT FSR-enabled (deleting an FSR snapshot
   fails; FSR must be disabled first via `disable-fast-snapshot-restores`).
8. `aws backup describe-backup-vault --backup-vault-name <name>` — for
   vault operations, capture `VaultType`, `LockState` (`Unlocked` /
   `Locked` / `Compliance`), `MinRetentionDays`, `MaxRetentionDays`.
9. `aws backup get-backup-plan --backup-plan-id <id>` — for plan
   operations, capture rules, target vault, schedule, lifecycle.
10. `aws dlm get-lifecycle-policy --policy-id <id>` — for DLM, capture
    `PolicyType` (`EBS_SNAPSHOT_MANAGEMENT` / `IMAGE_MANAGEMENT`), schedule,
    target tags, `PolicyDetails`.

**Malformed input:** if the input JSON is invalid or missing required fields,
emit `VERDICT: ERROR` with `REASON: Resource/operation configuration is not
valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with the appropriate `aws ec2 describe-*` / `aws
backup describe-*` / `aws dlm get-*` command in JSON output and re-plan.`

| Resource attribute | Effect on operation |
|---|---|
| Instance `State: running` | AMI create allowed with `--no-reboot` (crash-consistent) or default (reboot for app-consistent). |
| Instance `State: stopped` | AMI create produces an app-consistent AMI (no reboot needed). |
| Instance `State: shutting-down`, `terminated`, `pending` | BLOCKED — operation would fail. |
| Volume `State: in-use`, `Attachments` populated | Snapshot create OK; capture `DeleteOnTermination` for AMI launch fidelity. |
| Volume `State: available` (detached), `Attachments: []` | Snapshot create OK; the snapshot represents the detached state. |
| Volume `State: error`, `creating`, `deleting` | BLOCKED — transient; retry after `available` / `in-use`. |
| Snapshot `State: completed` | Safe to copy, share, delete, restore-from. |
| Snapshot `State: pending` | BLOCKED for any operation that needs the data (copy, restore). Wait via `aws ec2 wait snapshot-completed`. |
| Snapshot `State: error` | BLOCKED — snapshot failed; the data is not recoverable from this id. |
| Snapshot `StorageTier: archive` | Restore takes 24-72 hr (vs seconds for standard tier). Surface in plan. |
| Snapshot referenced by a registered AMI's `BlockDeviceMappings` | BLOCKED for `delete-snapshot` — deregister the AMI first. |
| Snapshot FSR-enabled | BLOCKED for `delete-snapshot` — disable FSR via `disable-fast-snapshot-restores` first. |
| AMI `State: available` | Safe to launch, copy, deregister. |
| AMI `State: pending`, `failed` | BLOCKED — wait or recreate. |
| AMI `DeprecationTime` in the past | AMI is deprecated; launches still work but UI/CLI flag it. Surface as a finding. |
| Encrypted snapshot cross-account share | Source KMS key policy MUST grant recipient; snapshot attribute alone is insufficient. |
| Backup vault `LockState: Compliance` | Immutable until retention expires — `DeleteBackupJob` returns `InvalidParameter`. Plan accordingly. |
| Backup vault `LockState: Governance` | Privileged roles can break retention. Surface this; do not assume WORM. |
| Backup vault `LockState: Unlocked` | No immutability — surface for compliance workloads that require WORM. |
| DLM policy `State: ENABLED` | Active — verify the schedule matches the operator intent. |
| DLM policy `State: ERROR` | Policy disabled due to repeated failures (often IAM role drift); investigate before relying on it. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious EC2/EBS backup behaviors

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

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is BLOCKED
with the failed checks enumerated in PRE_CHECKS. Do NOT execute the
operation.

**For ALL operations:**
1. Caller IAM role holds the required `ec2:*` / `backup:*` / `dlm:*`
   permissions for the target action.
2. Service quota for the operation is not exceeded (snapshot quota,
   AMI quota, FSR quota, AWS Backup concurrent jobs).
3. Source resource state is not transient (`pending`, `busy`, `error`).
4. The operation is not already in progress (no concurrent create-snapshot
   for the same volume that hasn't returned a snapshot-id).

**For `create-snapshot`:**
5. Volume `State: in-use` or `available` (not `creating`, `deleting`,
   `error`).
6. Snapshot `Description` is unique enough to track (or use a
   `copied-from`, `pre-migration`, `dlm-policy` tag for lineage).
7. (For application-consistent snapshots) Pre-step to quiesce I/O via
   `fsfreeze` (Linux) or VSS (Windows) — confirm the operator's plan.

**For `copy-snapshot` (cross-region or cross-account):**
5. Source snapshot `State: completed`.
6. Destination region opted-in (for opt-in regions like af-south-1,
   me-central-1, eu-south-1, ap-east-1, etc.).
7. Destination-region KMS key specified (for encrypted source) — passing
  the source-region KMS ARN fails.
8. Cross-account share: source KMS key policy grants recipient
   `kms:Decrypt` and `kms:CreateGrant`; snapshot attribute shared with
   recipient account ID.
9. Cost surfacing: per-GB transfer + destination-region storage.

**For `create-image`:**
5. Instance `State: running` or `stopped`. `running` requires the
   reboot-vs-no-reboot decision; `stopped` produces an app-consistent AMI.
6. All `BlockDeviceMappings` volumes `State: in-use`.
7. (Optional) Pre-step: stop the DB engine, flush writes, or call
   `fsfreeze` for application consistency.
8. AMI `Name` is unique within the account/region.
9. `--no-reboot` decision explicit (crash-consistent vs app-consistent).

**For `deregister-image`:**
5. AMI exists and `State: available` (or `failed`).
6. Operator confirmed the AMI is no longer needed (no ASG launch
   template, no EC2 Image Builder pipeline, no recent launches).
7. Snapshot cleanup plan enumerated (the AMI's `BlockDeviceMappings`
   snapshot-ids will be deleted in a follow-up `delete-snapshot` step).

**For `delete-snapshot`:**
5. Snapshot `State: completed` (or `error`, which is force-deletable).
6. NOT referenced by any registered AMI's `BlockDeviceMappings` —
   `describe-images --owners self --filters
   BlockDeviceMapping.SnapshotId=<id>` returns empty.
7. NOT FSR-enabled — `describe-fast-snapshot-restores --filters
   snapshot-id=<id>` returns empty. If FSR is enabled, run
   `disable-fast-snapshot-restores` first.
8. NOT the parent of an active DLM-managed chain (DLM will recreate; the
   delete is futile and may break the chain's reference tracking).

**For `create-backup-plan`:**
5. Target vault exists (`describe-backup-vault`).
6. Schedule cron is valid and in the intended timezone.
7. Lifecycle (move-to-cold, delete-after-days) is within the vault's
   min/max retention if vault-locked.
8. Backup selection (resources-by-tag or resource-arn list) is non-empty.
9. Cross-region/cross-account copy rules reference valid destination
   vaults.

**For `put-backup-vault-lock-config` (enable vault lock):**
5. `LockMode` is explicit (`COMPLIANCE` or `GOVERNANCE`).
6. `MinRetentionDays` and `MaxRetentionDays` are within the operator's
   compliance framework.
7. `ChangeableForDays` (cool-down period, default 72 hr) is understood —
   once it expires, compliance mode is irreversible.
8. Existing backups in the vault comply with the new retention window.

**For `create-lifecycle-policy` (DLM):**
5. `PolicyType` explicit (`EBS_SNAPSHOT_MANAGEMENT` or
   `IMAGE_MANAGEMENT`).
6. Schedule cron valid; target tags non-empty and match at least one
   resource.
7. IAM role for DLM (`AWS-DLM-LifeCycleRole` or equivalent) trusts
   `dlm.amazonaws.com` and has `ec2:CreateSnapshot`, `ec2:CreateTags`,
   `ec2:DeleteSnapshot` (for retention), etc.
8. Retention count is reasonable (e.g., 7 daily, 4 weekly, 12 monthly —
   NOT 9999).

**For `create-volume` (from snapshot):**
5. Source snapshot `State: completed`.
6. Destination AZ matches the target instance's AZ (for attach).
7. (For encrypted source) KMS key accessible.
8. (For resize) New `--size` >= snapshot size; shrinking is not allowed.

**For `run-instances` (from AMI):**
5. AMI `State: available`, NOT deprecated past a reasonable threshold.
6. Subnet, security group, key pair, IAM profile all exist.
7. Instance type compatible with the AMI architecture
   (`x86_64` vs `arm64` — Mac, graviton).
8. EBS volume mappings inherit or override the AMI's snapshots.
9. `BlockDeviceMappings[].Ebs.DeleteOnTermination` set explicitly
   (`false` for stateful, `true` for ephemeral).

**For `start-restore-job` (AWS Backup):**
5. Recovery point ARN valid and `Status: COMPLETED`.
6. Restore target (vault, IAM role, metadata) populated.
7. For EC2 restores: subnet, security group, instance type specified in
   the metadata (the recovery point's metadata is the default).

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI sequence
and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the source
  resource configuration.
- The expected duration (snapshot create ~1 min/100 GB; AMI create same;
  cross-region copy data-transfer-bound; AWS Backup restore minutes-to-
  hours).
- The expected side-effects (new snapshot-id / AMI-id / volume-id /
  instance-id / restore-job-id; reboot vs no-reboot for AMI).
- The CONFIRM gate prompt.

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

### Step 4: Post-verification — COMPLETED

After the operation finishes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `describe-snapshots --snapshot-ids <id>` — confirm `State: completed`.
2. `describe-images --image-ids <id>` — confirm `State: available`.
3. `describe-volumes --volume-ids <id>` — confirm `State: available` (pre-
   attach) or `in-use` (post-attach).
4. `describe-instances --instance-ids <id>` — confirm `State: running`.
5. For AWS Backup restore: `describe-restore-job --restore-job-id <id>` —
   confirm `Status: COMPLETED` and the created resource ARN.
6. For cross-account/cross-region: verify the recipient can `describe` and
   `create-volume`/`run-instances` from the new resource.
7. For application-consistent restore: fsck the volume, mount, and run a
   sentinel query (database checksum, file count).
8. Clean up temporary resources (verification volumes, restored instances).
9. Plan follow-up: tag the new resource, schedule lifecycle transition
   (archive tier, DLM policy attachment, AWS Backup plan attachment).

If ANY verification fails, emit `VERDICT: ERROR` with the failure details
— do not claim COMPLETED.

## Output format (per operation)

```text
OPERATION: <create-snapshot | copy-snapshot | create-image | deregister-image | delete-snapshot | create-backup-plan | enable-vault-lock | create-dlm-policy | restore-volume | restore-from-ami | start-restore-job>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <instance-id | volume-id | snapshot-id | AMI-id | vault-name | policy-id>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NEW_RESOURCE: <new snapshot-id / AMI-id / volume-id / instance-id / restore-job-id, or "(none)">
REBOOT: <yes | no | n/a>
NOTES: <cost, lineage tags, cleanup, follow-ups>
```

### Worked example — pre-migration AMI from a running instance

```text
OPERATION: create-image
VERDICT: READY
TARGET: i-0prodapp123456789ab (running, prod webapp)
PRE_CHECKS:
  - [PASS] Instance State running (AMI create allowed)
  - [PASS] All 3 attached volumes State in-use
  - [PASS] AMI Name "prod-webapp-pre-migration-2026-08-07" is unique
    (describe-images --owners self --filters Name=name,
    Values=prod-webapp-pre-migration-2026-08-07 returns empty)
  - [PASS] Caller holds ec2:CreateImage on the instance ARN
  - [PASS] Caller decided: --no-reboot=true (crash-consistent accepted,
    webapp is stateless; DB has its own snapshot)
STEPS:
  1. CONFIRM: About to create-image from i-0prodapp123456789ab in
     account 111111111111 region us-east-1. With --no-reboot=true, the
     instance will NOT be rebooted (crash-consistent AMI). Estimated
     duration: ~5 minutes (3 volumes, ~500 GB total). Proceed? (yes/no)
  2. aws ec2 create-image \
       --instance-id i-0prodapp123456789ab \
       --name "prod-webapp-pre-migration-2026-08-07" \
       --description "Pre-migration capture; webapp + logs + data volumes" \
       --no-reboot \
       --tag-specifications "ResourceType=image,Tags=[{Key=source-instance,Value=i-0prodapp123456789ab},{Key=purpose,Value=pre-migration},{Key=delete-after,Value=2026-09-07}]" "ResourceType=snapshot,Tags=[{Key=source-instance,Value=i-0prodapp123456789ab},{Key=purpose,Value=pre-migration}]"
  3. aws ec2 wait image-available --image-ids <ImageId from step 2>
POST_VERIFY:
  - (pending execution)
  - aws ec2 describe-images --image-ids <ImageId> → State: available
  - aws ec2 describe-snapshots --snapshot-ids <snap-id-1>,<snap-id-2>,<snap-id-3>
    → all State: completed
  - Test-launch a t3.medium from the new AMI into a dev subnet to verify
    bootability
NEW_RESOURCE: (pending — will be ami-0new1234567890abcd)
REBOOT: no (--no-reboot=true; crash-consistent AMI)
NOTES:
  - The AMI references 3 snapshots; cleanup requires deregister-image
    AND delete-snapshot per snapshot when the AMI is no longer needed.
  - Tag delete-after=2026-09-07 triggers automated cleanup via a
    scheduled Lambda; review before enabling auto-cleanup.
  - For an app-consistent AMI, re-run without --no-reboot (reboots the
    source instance ~2 min).
  - Launch-permissions: AMI is private by default; use
    modify-image-attribute --launch-permission to share.
```

### Worked example — cross-account encrypted snapshot share BLOCKED

```text
OPERATION: copy-snapshot (cross-account, encrypted)
VERDICT: BLOCKED
TARGET: snap-0enc1234567890abc -> recipient account 222222222222
PRE_CHECKS:
  - [PASS] Snapshot State completed
  - [PASS] Snapshot Encrypted with KMS key arn:aws:kms:us-east-1:111111111111:key/abc
  - [PASS] Snapshot attribute createVolumePermission includes
    222222222222 (shared with recipient)
  - [FAIL] KMS key policy for arn:aws:kms:us-east-1:111111111111:key/abc
    does NOT grant 222222222222 kms:Decrypt or kms:CreateGrant.
    Recipient can describe-snapshots but cannot create-volume or
    copy-snapshot — the data is unreadable.
  - [PASS] Destination region us-west-2 opted-in
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
NEW_RESOURCE: (none)
REBOOT: n/a
NOTES:
  - Update the source account's KMS key policy to grant the recipient:
      {
        "Sid": "Allow recipient account to use the snapshot",
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
        "Action": ["kms:Decrypt", "kms:CreateGrant", "kms:DescribeKey"],
        "Resource": "*"
      }
    Then re-fetch: aws kms get-key-policy --key-id <key-id>
    --policy-name default.
  - OR re-issue the snapshot unencrypted via copy-snapshot --encrypted
    is NOT possible (encryption is immutable per resource); instead
    create a new unencrypted snapshot from the volume directly.
  - For cross-region: the recipient will additionally need to re-encrypt
    with their own KMS key in the destination region during copy-snapshot.
```

### Worked example — AWS Backup restore job

```text
OPERATION: start-restore-job (AWS Backup, EC2)
VERDICT: READY
TARGET: arn:aws:backup:us-east-1:111111111111:recovery-point:1a2b3c-4d5e-6f7g
PRE_CHECKS:
  - [PASS] Recovery point Status COMPLETED
  - [PASS] Recovery point ResourceArn is the source EC2 instance
  - [PASS] Restore IAM role arn:aws:iam::111111111111:role/service-role/AWSBackupRestoreRole
    trusts backup.amazonaws.com
  - [PASS] Metadata includes InstanceType, SubnetId, SecurityGroupIds,
    IamInstanceProfile (recovery-point defaults are valid)
  - [PASS] Target subnet has capacity for the instance type
STEPS:
  1. CONFIRM: About to start-restore-job from recovery-point
     1a2b3c-4d5e-6f7g in account 111111111111 region us-east-1. This
     will create a NEW EC2 instance with NEW volume-ids and a NEW ENI
     (original instance unchanged). Estimated duration: 15-30 minutes.
     Proceed? (yes/no)
  2. aws backup start-restore-job \
       --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1a2b3c-4d5e-6f7g \
       --iam-role-arn arn:aws:iam::111111111111:role/service-role/AWSBackupRestoreRole \
       --metadata '{"InstanceType":"t3.large","SubnetId":"subnet-0prod","SecurityGroupIds":["sg-0prod"],"IamInstanceProfile":"arn:aws:iam::111111111111:instance-profile/prod-webapp","DeleteOnTermination":"false"}' \
       --resource-type EC2
  3. aws backup wait restore-job-completed --restore-job-id <RestoreJobId from step 2>
POST_VERIFY:
  - (pending execution)
  - aws backup describe-restore-job --restore-job-id <RestoreJobId>
    → Status: COMPLETED, CreatedResourceArn: arn:aws:ec2:...
  - aws ec2 describe-instances --instance-ids <instance-id from CreatedResourceArn>
    → State: running
  - Verify application on the new instance (HTTP 200, DB connectivity)
  - Plan connection-string cutover: original instance continues to bill
NEW_RESOURCE: (pending — will be a new EC2 instance-id and restore-job-id)
REBOOT: n/a (new instance)
NOTES:
  - The new instance has a NEW private IP (unless explicitly assigned).
    Update DNS, secrets manager, and connection strings atomically.
  - DeleteOnTermination=false on the root volume preserves data on
    instance termination.
  - Tag the restored instance with restored-from=<recovery-point-arn>
    and delete-after for cleanup.
  - Original instance unchanged — plan decommission separately.
```

### Worked example — DLM policy creation

```text
OPERATION: create-lifecycle-policy (DLM)
VERDICT: READY
TARGET: tag:BackupSchedule=daily (10 volumes match)
PRE_CHECKS:
  - [PASS] PolicyType EBS_SNAPSHOT_MANAGEMENT
  - [PASS] Schedule cron rate(1 day) valid; create-interval 24h
  - [PASS] Target tags Key=BackupSchedule,Values=daily → 10 volumes match
    (verified via ec2 describe-volumes --filters)
  - [PASS] IAM role AWS-DLM-LifeCycleRole exists, trusts dlm.amazonaws.com,
    has ec2:CreateSnapshot/CreateTags/DeleteSnapshot on the volume ARNs
  - [PASS] Retention count 7 (7 daily snapshots), reasonable
  - [PASS] Copy-tags-from-source=true (lineage preserved)
  - [PASS] Cross-region copy NOT configured (single-region policy)
STEPS:
  1. CONFIRM: About to create-lifecycle-policy in account 111111111111
     region us-east-1. This will take a daily snapshot of 10 volumes
     tagged BackupSchedule=daily, retain 7 snapshots per volume (~70 GB-
     month added storage initially). Proceed? (yes/no)
  2. aws dlm create-lifecycle-policy \
       --description "Daily snapshots of volumes tagged BackupSchedule=daily" \
       --state ENABLED \
       --execution-role-arn arn:aws:iam::111111111111:role/service-role/AWS-DLM-LifeCycleRole \
       --policy-details '{
         "PolicyType": "EBS_SNAPSHOT_MANAGEMENT",
         "ResourceTypes": ["VOLUME"],
         "TargetTags": [{"Key": "BackupSchedule", "Value": "daily"}],
         "Schedules": [{
           "Name": "Daily",
           "CreateRule": {"Interval": 24, "IntervalUnit": "HOURS", "Times": ["03:00"]},
           "RetainRule": {"Count": 7},
           "CopyTags": true,
           "FastRestoreRule": {"Interval": 0, "IntervalUnit": "HOURS"}
         }]
       }'
  3. aws dlm get-lifecycle-policy --policy-id <PolicyId from step 2>
POST_VERIFY:
  - (pending first execution at 03:00 UTC)
  - aws dlm get-lifecycle-policy --policy-id <PolicyId>
    → State: ENABLED, no recent failures
  - After 03:00 UTC: aws ec2 describe-snapshots --owner-ids self
    --filters Name=tag:dlm:policy,Values=<PolicyId> → 10 snapshots State completed
NEW_RESOURCE: (pending — will be a DLM policy-id)
REBOOT: n/a
NOTES:
  - DLM does NOT capture instance metadata (AMI is the right tool for
    that). Use PolicyType=IMAGE_MANAGEMENT for instance-level DLM.
  - Retain count 7 keeps 7 daily snapshots; older snapshots auto-deleted.
  - Review the policy weekly for `State: ERROR` (often IAM role drift).
  - For cross-region DR via DLM, add a `CrossRegionCopyRule` (separate
    region, separate KMS key).
```

## Anti-Patterns — NEVER do these things

- NEVER tell an operator "the storage cost drops immediately after
  `delete-snapshot`." EBS snapshots are incremental; deleting a snapshot
  is safe but its unique blocks migrate to later snapshots that reference
  them. Cost saving may lag by weeks.

- NEVER recommend `deregister-image` as the full AMI cleanup. Deregister
  removes only the metadata; the EBS snapshots in the AMI's
  `BlockDeviceMappings` persist and bill. Full cleanup is deregister +
  `delete-snapshot` per EBS-mapping snapshot.

- NEVER `delete-snapshot` without first checking AMI references
  (`describe-images --owners self --filters BlockDeviceMapping.SnapshotId=<id>`)
  AND FSR status (`describe-fast-snapshot-restores`). Deleting an
  AMI-referenced snapshot bricks launches; deleting an FSR-enabled
  snapshot fails.

- NEVER assume "vault-locked" means WORM. Compliance mode is immutable;
  governance mode is a guardrail that privileged roles can break. Always
  surface the `LockState` explicitly (`Compliance` vs `Governance`) so
  compliance auditors don't assume the wrong thing.

- NEVER share an encrypted snapshot cross-account without verifying the
  source KMS key policy grants the recipient `kms:Decrypt` and
  `kms:CreateGrant`. The snapshot attribute alone is insufficient — the
  recipient can describe but cannot create-volume or copy.

- NEVER copy a snapshot cross-region without surfacing the cost. Cross-
  region copy bills $0.02/GB transfer + destination-region storage. A
  1 TB snapshot copied to 3 DR regions is $60 transfer + 3 TB-month
  ongoing.

- NEVER copy a snapshot cross-region using the source-region KMS key ARN.
  KMS keys are regional; the destination region needs its own KMS key
  via `--kms-key-id`.

- NEVER run `create-image` without `--no-reboot` decision being explicit.
  Default (no flag) reboots the source for app-consistency;
  `--no-reboot=true` produces a crash-consistent AMI. For databases,
  app-consistency requires either the reboot or a pre-step (stop DB,
  fsfreeze).

- NEVER set `DeleteOnTermination: true` on a stateful data volume when
  launching from an AMI. Terminating the instance destroys the data.
  Set `BlockDeviceMappings[].Ebs.DeleteOnTermination=false` for
  persistent data volumes.

- NEVER use snapshot Archive tier for DR. Archive snapshots cost less
  ($0.0125/GB-mo vs $0.05/GB-mo standard) but restore takes 24-72 hr —
  far too long for DR. Keep a standard-tier copy in the DR region.

- NEVER assume AWS Backup restore reuses the original instance IP,
  volume-ids, or ENI. Restore creates a NEW instance with NEW resources.
  Plan connection-string cutover atomically.

- NEVER enable FSR on snapshots that don't gate latency-sensitive launches.
  FSR bills $0.06/hr per AZ per snapshot (~$43.20/AZ-month) regardless
  of use. A 100 GB snapshot with FSR in 3 AZs is $129.60/month of FSR
  vs $5/month of storage.

- NEVER tell a compliance auditor "we have immutable backups" without
  verifying the vault lock mode AND retention window. Governance mode +
  privileged role = NOT immutable. Compliance mode + cool-down passed =
  immutable.

- NEVER use `describe-snapshots` without `--owner-ids self` for inventory.
  Without it, the call returns every public snapshot in the world and is
  throttled.

- NEVER bulk-restore snapshots without testing one first. A 100-snapshot
  bulk restore can run concurrently and saturate EBS creation bandwidth;
  test-restore a single volume first to verify consistency and duration.

- NEVER assume AMI launch permission implies snapshot create-volume
  permission. Sharing an AMI does NOT share its underlying snapshots;
  the recipient can launch but cannot create-volume directly from the
  AMI's snapshot-ids. Use `modify-snapshot-attribute` separately.

- NEVER auto-execute a state-changing EC2/AWS Backup CLI without the
  CONFIRM gate. AMI create may reboot the source; snapshot delete is
  irreversible; vault lock is irreversible in compliance mode.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-snapshot`, `copy-snapshot`, `create-image`, `deregister-image`,
  `delete-snapshot`, `create-backup-plan`, `put-backup-vault-lock-config`,
  `create-lifecycle-policy`, `create-volume`, `run-instances`,
  `start-restore-job`), emit: `CONFIRM: About to <operation> on <target>
  in account <account> region <region>. This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.

- **Snapshot pre-state for rollback.** Before any AMI create or volume
  modification: `aws ec2 describe-volumes --volume-ids <id> --output
  json > /tmp/<id>-pre-$(date +%s).json`. EBS state is not versioned.

- **Verify AMI references before snapshot delete.** Always run
  `describe-images --owners self --filters BlockDeviceMapping.SnapshotId=<id>`
  AND `describe-fast-snapshot-restores --filters Name=snapshot-id,Values=<id>`.
  Both must return empty.

- **Verify KMS key policy before cross-account share.** The source
  account's KMS key policy must grant the recipient `kms:Decrypt` and
  `kms:CreateGrant`. Verify via `aws kms get-key-policy --key-id <id>
  --policy-name default`.

- **Verify vault lock mode before relying on immutability.** Compliance
  mode + cool-down passed = immutable; governance mode = breakable by
  privileged roles. Surface the `LockState` in every plan.

- **Verify instance type compatibility before AMI launch.** AMI
  architecture (`x86_64` vs `arm64` vs Mac) must match the instance
  type. Graviton AMIs do not launch on Intel instances.

- **Verify subnet capacity before AWS Backup restore.** The target
  subnet must have capacity for the instance type; restore fails if the
  subnet is at its IP limit.

- **Plan connection-string cutover before restore completes.** Restore
  produces a new instance with new volume-ids, new ENI, and potentially
  new private IP. Application connection strings, DNS aliases, and
  secrets must be updated atomically with the cutover.

- **Prefer reversible changes.** Tag (`audit:review-required`,
  `retainUntil`) before deleting — a tagged resource is recoverable; a
  deleted snapshot is not.

- **Rate-limit bulk operations.** EBS snapshot creation has a per-volume
  concurrency limit (one concurrent create per volume). Bulk DLM
  schedules stagger automatically; manual bulk-create must be staggered.

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

## Domain

AWS CloudOps / EC2, EBS, AMI, AWS Backup & DLM Backup/Restore.

## AWS documentation

- **Amazon EC2 User Guide** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Concepts.html
- **Amazon EBS snapshots** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EBSSnapshots.html
- **Amazon Machine Images (AMIs)** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html
- **Fast Snapshot Restore** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-fast-snapshot-restore.html
- **Archive Amazon EBS snapshots** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snapshot-archive.html
- **AWS Backup Developer Guide** — https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html
- **AWS Backup Vault Lock** — https://docs.aws.amazon.com/aws-backup/latest/devguide/vaults.html#vault-lock
- **AWS Backup Point-in-Time Recovery** — https://docs.aws.amazon.com/aws-backup/latest/devguide/point-in-time-recovery.html
- **Data Lifecycle Manager** — https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/snapshot-lifecycle.html
- **AWS CLI Command Reference: ec2 / backup / dlm** — https://docs.aws.amazon.com/cli/latest/reference/ec2/ / .../backup/ / .../dlm/
