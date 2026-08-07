---
description: Operate EC2 backup and snapshot workflows — EBS snapshots, AMI creation and lifecycle, AWS Backup plans and vaults with vault lock, DLM lifecycle policies, point-in-time recovery, and restore procedures — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
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
routes_to: ec2-backup-operator
---

# /aws:operate-ec2-backup

Activate the `ec2-backup-operator` skill and plan/execute an EC2 backup,
snapshot, AMI, AWS Backup, or DLM operation with deterministic pre-
checks, CONFIRM gate, and post-verification.

## What it does

Reads a resource + operation request and applies the priority-ordered
pre-check sequence:

1. Pre-flight resource metadata gate — short-circuit `pending`/`error`
   states, AMI references, FSR status, vault lock mode.
2. Pre-check gate — BLOCKED if any check fails (instance not in valid
   state, volume detached, AMI references the snapshot being deleted,
   KMS key policy missing for cross-account copy, snapshot quota
   exceeded, vault lock in governance mode blocks the caller).
3. READY — emit the exact `aws ec2` / `aws backup` / `aws dlm` CLI
   sequence with all flags populated, expected side-effects (reboot,
   new volume-id, restore job-id, FSR cost), and the CONFIRM gate
   prompt.
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI,
   wait via the appropriate waiter (`snapshot-completed`,
   `image-available`, `volume-available`, `instance-running`,
   `restore-job-completed`).
5. Post-verification — `describe-snapshots`, `describe-images`,
   `describe-volumes`, `describe-instances`, `describe-restore-job`,
   fsck / sentinel query for application consistency. COMPLETED only
   if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

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
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NEW_RESOURCE: <new snapshot-id / AMI-id / volume-id / instance-id / restore-job-id>
REBOOT: <yes | no | n/a>
NOTES: <cost, lineage tags, cleanup, follow-ups>
```

## When to invoke

Paste a resource + operation request, or just describe the scenario and
ask any of:

- "create a pre-migration AMI"
- "take a snapshot of this volume before the change"
- "copy this snapshot to the DR region"
- "share this snapshot with account 222222222222"
- "enable vault lock on the prod-ec2-vault"
- "create a DLM daily-snapshot policy"
- "restore a volume from snap-0xxx"
- "launch a replacement instance from ami-0yyy"
- "start an AWS Backup restore job"
- "diagnose why this snapshot is stuck in pending"

A bare resource-id + any operation verb ("snapshot this volume", "make
an AMI from this instance") also routes here via the orchestrator.

## Inputs

- Operation: `create-snapshot`, `copy-snapshot`, `create-image`,
  `deregister-image`, `delete-snapshot`, `create-backup-plan`,
  `put-backup-vault-lock-config`, `create-lifecycle-policy`,
  `create-volume`, `run-instances`, `start-restore-job`.
- Target: instance-id, volume-id, snapshot-id, AMI-id, vault-name, or
  policy-id.
- Source resource metadata (state, encryption, KMS key, attachments,
  block-device-mappings, AMI references, FSR status, vault lock state).
- Reboot tolerance: `--no-reboot=true|false` for AMI create.
- (For AWS Backup) recovery-point ARN, restore IAM role, target subnet.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected duration, expected side-
  effects (reboot, new resource IDs, cost), and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the new
  resource IDs, fsck/sentinel verification, and cleanup plan.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., deregister the AMI first, update the KMS key policy, disable
  FSR).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Operate specialist for EC2/EBS/AMI/AWS Backup/DLM).
- `/aws:audit-ebs-volume` for the upstream EBS volume posture audit —
  encryption, attachment state, gp3 modernity — to run before backups.
- `/aws:audit-backup-plan` for the AWS Backup plan audit — vault lock,
  retention, cross-region copy — complementing this operate skill.
- `/aws:operate-rds-backup-restore` for RDS/Aurora-specific backup and
  restore (separate data-plane from EC2/EBS).
