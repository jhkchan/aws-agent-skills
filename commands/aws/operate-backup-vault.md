---
description: Operate AWS Backup vault lifecycles — create vaults, apply vault locks, author backup plans, manage selections, run restores with pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "create AWS Backup vault"
  - "lock backup vault"
  - "compliance mode backup vault"
  - "governance mode backup vault"
  - "WORM backup vault"
  - "retention lock"
  - "create backup plan"
  - "backup policy"
  - "backup selection by tag"
  - "cross-region copy backup"
  - "point-in-time recovery"
  - "PITR EC2"
  - "continuous backup EC2"
  - "restore from backup"
  - "cross-region restore"
  - "start restore job"
  - "diagnose failed backup job"
  - "Backup Search"
  - "AWS Backup for FSx"
routes_to: backup-vault-operator
---

# /aws:operate-backup-vault

Activate the `backup-vault-operator` skill and plan/execute an AWS
Backup vault operation with deterministic pre-checks, CONFIRM gate,
and post-verification.

## What it does

Reads a vault operation spec plus the intended operation and applies
the priority-ordered pre-check sequence:

1. Pre-flight vault/KMS/IAM metadata gate — short-circuit cases where
   the KMS key is disabled, the vault is already in compliance lock,
   or the recovery point has expired.
2. Pre-check gate — BLOCKED if any check fails (KMS key disabled,
   compliance-mode lock irreversibility, IAM permission missing,
   lifecycle out of retention-window range, recovery point expired,
   destination region vault missing).
3. READY — emit the exact CLI sequence with all flags populated, the
   expected duration (snapshot vs PITR vs cold restore), the expected
   side-effects (new recovery point, new restored resource, locked
   vault), and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — snapshot `describe-backup-vault`
   first (for lock changes; no rollback path after grace), execute
   the CLI, wait for `describe-restore-job` or
   `describe-backup-job` to reach terminal state.
5. Post-verification — recovery point or restore job COMPLETED,
   CreatedResourceArn populated, vault lock reflected.
   COMPLETED only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <create-vault | lock-vault | create-plan | create-selection | start-backup | start-restore | enable-pitr | diagnose>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <vault-name or resource-arn>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <vault lock state, recovery point status, restore job status>
NOTES: <compliance-vs-governance rationale, retention window, recovery time estimate, cross-region copy caveats>
```

## When to invoke

Paste a vault operation spec and ask any of:

- "create a backup vault with KMS encryption"
- "lock this vault in COMPLIANCE mode for CIS 3.6"
- "create a backup plan with cross-region DR copy"
- "build a tag-based backup selection"
- "start a PITR restore for this EC2 instance"
- "diagnose why backup job abc123 failed"
- "enable continuous backups for EC2"

A bare vault name + any operation verb ("lock this vault", "restore
from this recovery point") also routes here via the orchestrator.

## Inputs

- **Required (varies by operation):**
  - **create-vault:** vault name, region, KMS key ARN.
  - **lock-vault:** vault name, mode (COMPLIANCE | GOVERNANCE),
    MinRetentionDays, MaxRetentionDays, ChangeableForDays.
  - **create-plan:** plan name, target vault, schedule, lifecycle
    (cold storage + delete days), copy actions (destination region,
    destination vault, destination lifecycle).
  - **create-selection:** plan ID, selection name, IAM role ARN,
    conditions (ListOfTags, Resources, or Conditions).
  - **start-backup:** vault, resource ARN, IAM role ARN.
  - **start-restore:** vault, recovery point ARN, resource type,
    metadata (resource-type-specific), IAM role ARN, optional
    RestoreTime (PITR).
  - **enable-pitr:** plan name, vault, rule with `ContinuousBackup:
    true`, AdvancedBackupSettings for the resource type.
  - **diagnose:** vault name and/or backup-job-id /
    restore-job-id.

## Outputs

- One VERDICT block per operation (READY, BLOCKED, or COMPLETED).
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected duration, expected
  side-effects, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the
  resulting resource ARN (for restore), the vault lock state (for
  lock operations), and any follow-up tuning recommendations.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., use COMPLIANCE mode for HIPAA, add KMS key policy grant,
  re-enable KMS key).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for AWS Backup vault lifecycle).
- `/aws:audit-backup-plan` for the audit/classification side — the
  auditor finds mis-configured backup plans and unlocked vaults;
  this operator creates, locks, and restores them.
- `/aws:operate-ec2-backup` for EC2-specific backup operations
  (snapshots, AMI lifecycle).
- `/aws:operate-rds-backup-restore` for RDS-specific backup/restore.
- `/aws:operate-dynamodb-backup` for DynamoDB on-demand backup /
  PITR.
