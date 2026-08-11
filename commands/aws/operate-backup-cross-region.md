---
description: Operate AWS Backup cross-region and cross-account operations — add cross-region copy rules to backup plans, configure cross-account copy via Organizations, restore from cross-region recovery points, deploy DR vault locks, enable continuous cross-region backups, with pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "cross-region copy backup"
  - "DR copy backup plan"
  - "cross-account backup"
  - "AWS Organizations backup policy"
  - "cross-region restore"
  - "restore from DR region"
  - "destination region backup"
  - "destination vault backup"
  - "backup vault lock cross-region"
  - "DR vault compliance"
  - "continuous backup cross-region"
  - "PITR cross-region"
  - "copy action backup plan"
  - "external KMS key backup"
  - "cross-account restore"
  - "backup start-copy-job"
routes_to: backup-cross-region-operator
---

# /aws:operate-backup-cross-region

Activate the `backup-cross-region-operator` skill and plan/execute
an AWS Backup cross-region or cross-account operation with
deterministic pre-checks, CONFIRM gate, and post-verification.

## What it does

Reads a cross-region operation spec plus the intended operation and
applies the priority-ordered pre-check sequence:

1. Pre-flight destination vault + KMS + IAM metadata gate —
   short-circuit cases where the destination vault is missing,
   the destination KMS key is disabled, the source IAM role lacks
   `backup:CopyIntoBackupVault`, or the destination region is not
   opt-in.
2. Pre-check gate — BLOCKED if any check fails (destination vault
   missing, KMS key disabled, source IAM lacks
   `backup:StartCopyJob`, accounts not in same org, recovery point
   EXPIRED, DR vault already in COMPLIANCE lock, region not
   opt-in).
3. READY — emit the exact CLI sequence with all flags populated,
   the expected duration (minutes to hours depending on size), the
   expected side-effects (new recovery point in destination vault,
   new restored resource in destination region, locked DR vault),
   and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — snapshot
   `describe-backup-vault` first (for lock changes; no rollback
   path after grace), execute the CLI, wait for
   `describe-copy-job` or `describe-restore-job` to reach terminal
   state.
5. Post-verification — copy job COMPLETED with
   DestinationRecoveryPointArn populated, restore job COMPLETED
   with CreatedResourceArn populated, DR vault lock reflected.
   COMPLETED only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <add-copy-rule | start-copy | cross-account-enable | start-cross-region-restore | lock-dr-vault | enable-continuous-cross-region | diagnose>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <source-vault / destination-vault / copy-job-id / restore-job-id>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <copy job state, recovery point status in destination, restore job status, vault lock state in destination>
NOTES: <region-binding caveat, KMS ownership rationale, org-mode requirement, inter-region bandwidth estimate, cost impact>
```

## When to invoke

Paste a cross-region operation spec and ask any of:

- "add a cross-region copy rule to this plan"
- "start a manual copy to the DR region"
- "configure cross-account backup via Organizations"
- "restore from the DR region"
- "apply COMPLIANCE-mode lock on the DR vault"
- "enable continuous backups cross-region"
- "diagnose why my cross-region copy job is stuck"

A bare vault name + any cross-region verb ("copy to DR region",
"restore from DR vault") also routes here via the orchestrator.

## Inputs

- **Required (varies by operation):**
  - **add-copy-rule:** plan name, source region/vault, destination
    region/vault ARN, destination KMS key, copy rule lifecycle.
  - **start-copy:** source region/vault, recovery point ARN,
    destination region/vault ARN, IAM role.
  - **cross-account-enable:** source account, destination account,
    Organizations BACKUP_POLICY content.
  - **start-cross-region-restore:** destination region (where the
    recovery point lives), vault, recovery point ARN, resource
    type, metadata, IAM role.
  - **lock-dr-vault:** destination region, vault name, mode
    (COMPLIANCE | GOVERNANCE), MinRetentionDays, MaxRetentionDays,
    ChangeableForDays.
  - **enable-continuous-cross-region:** plan name with
    ContinuousBackup: true and CopyActions in the same rule.
  - **diagnose:** copy-job-id or restore-job-id + region.

## Outputs

- One VERDICT block per operation (READY, BLOCKED, or COMPLETED).
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason
  for failure.
- For READY: the exact CLI sequence, expected duration, expected
  side-effects, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the
  copy job DestinationRecoveryPointArn (for copy), the
  CreatedResourceArn (for restore), the DR vault lock state (for
  lock operations), and any follow-up DR drill recommendations.
- For BLOCKED: the specific failure reason and the remediation
  step (e.g., invite destination to org for cross-account, fix KMS
  policy grants, re-enable destination KMS key).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill
  is the Phase 4 Operate specialist for AWS Backup cross-region
  operations).
- `/aws:operate-backup-vault` for single-region vault operations
  (create vault, lock vault, plan, restore within the same region).
- `/aws:audit-backup-plan` for the audit/classification side — the
  auditor finds mis-configured cross-region copy rules; this
  operator creates, locks, and restores them.
