---
name: backup-vault-operator
description: Operates AWS Backup vault lifecycles — creates vaults with KMS encryption and tags, applies vault locks (compliance WORM vs governance soft lock with MinRetentionDays / MaxRetentionDays / ChangeableForDays), authors backup plans (schedule, cold-storage lifecycle, cross-region copy), manages selections (tag-based, resource-ARN, Conditions), starts restore jobs (PITR, cross-region, restore-to-new), and operates latest features (continuous backups for EC2 PITR, Backup Search, AWS Backup for FSx). Runs pre-checks (KMS key enabled, vault lock state, IAM permissions, recovery point COMPLETED), emits the exact backup:create-backup-vault / put-backup-vault-lock-configuration / create-backup-plan / start-restore-job CLI behind a CONFIRM gate, and verifies state post-apply. Emits a verdict (READY | BLOCKED | COMPLETED). Use when creating a vault, locking for compliance (CIS 3.6, NIST CP-9), scheduling cross-region DR, running a PITR restore drill, diagnosing a failed job, or enabling continuous backups.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws backup create-backup-vault, put-backup-vault-lock-configuration, create-backup-plan, create-backup-selection, start-backup-job, start-restore-job, describe-backup-job, describe-restore-job, list-recovery-points-by-backup-vault, list-backup-plans, list-backup-selections, get-backup-plan-from-json, describe-backup-vault...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Storage
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  when_to_use: Creating or locking a backup vault (compliance vs governance mode), authoring backup plans (schedule, lifecycle, cross-region copy), building backup selections (by tag, resource ID, conditions), starting point-in-time or cross-region restores, running restore drills, diagnosing failed backup jobs or stuck restore jobs, enabling continuous backups for EC2 PITR, deploying AWS Backup for FSx, or using Backup Search across recovery points.
  activation_triggers: create AWS Backup vault, lock backup vault, compliance mode backup vault, governance mode backup vault, WORM backup vault, retention lock, create backup plan, backup policy, backup selection by tag, cross-region copy backup, point-in-time recovery, continuous backup EC2, restore from backup, cross-region restore, start restore job, diagnose failed backup job, Backup Search, AWS Backup for FSx
  invocation_schema: 'Input: either (a) a backup operation intent (create-vault, lock-vault, create-plan, create-selection, start-backup, start-restore, enable-pitr, diagnose) with target vault name, KMS key ARN, schedule, retention window, and resource scope; OR (b) an existing vault name + recovery point ID for live-account restore or diagnosis. Output: deterministic OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Backup, backup vault, vault lock, compliance mode, governance mode, WORM, retention lock, backup plan, backup policy, backup selection, tag-based backup, cross-region copy, lifecycle, cold storage, point-in-time recovery, PITR, continuous backup, EC2 PITR, Backup Search, Amazon FSx backup, recovery point, restore job, cross-region restore, backup reports, backup compliance, KMS encryption, backup vault KMS
  tags: aws-backup, storage, operate, vault-lock, backup-plan, backup-selection, restore, pitr, compliance-mode, kms, cross-region-copy, fsx, backup-search
---

# Backup Vault Operator

## What this skill does

Executes AWS Backup vault operations correctly and safely — vault
creation, vault lock (compliance vs governance), backup plans, backup
selections, restore jobs, and report auditing. Runs deterministic
pre-checks before any state-changing CLI, emits the exact
`backup:*` CLI sequence behind a CONFIRM gate, and verifies recovery
points and restore job state after apply. Every operation surfaces the
mode (compliance vs governance), retention window, and the
immutability posture so the operator knows what is reversible.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority + recovery time baselines | Before any operation |
| **§ Mindset** | Compliance-vs-governance lock, PITR vs snapshot, vault-region binding | Understanding the safety model |
| **§ Pre-flight** | Vault/KMS/IAM metadata gate | Before executing any CLI |
| **§ Process** | Per-operation planning: vault, lock, plan, selection, restore, PITR, diagnose | When choosing which operation |
| **§ Common patterns** | Vault create, compliance lock, plan with cross-region copy, PITR enable, restore drill | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, COMMANDS, POST_VERIFY | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes | Review before risky operations |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (KMS key disabled, vault already in compliance lock, IAM `backup:StartBackupJob` missing, no recovery point in target vault, region mismatch, overlapping backup selection) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Operation applied and post-verification passed (recovery point generated, restore job COMPLETED, vault lock configuration reflected, backup plan ARN returned) | Emit describe output, lock state, retention window |

**Priority order for pre-checks (all must pass for READY):**

1. **Vault exists and is reachable** — `describe-backup-vault` returns
   the vault in the same account+region as the operation.
2. **KMS key state** — `kms describe-key` returns `Enabled` (not
   `Disabled` / `PendingDeletion`); key policy grants
   `kms:GenerateDataKey` and `kms:Decrypt` to
   `backup.<region>.amazonaws.com`.
3. **Vault lock state** — `describe-backup-vault` `VaultLock` shows
   whether compliance mode is active. If `LockState: LOCKED` in
   compliance mode, the retention window is immutable — pre-check must
   flag any operation that would shorten retention or change the lock.
4. **IAM permissions** — caller has `backup:CreateBackupVault`,
   `PutBackupVaultLockConfiguration`, `CreateBackupPlan`,
   `CreateBackupSelection`, `StartBackupJob`, `StartRestoreJob` as
   appropriate.
5. **Resource assignment scope** — `list-backup-selections` shows no
   overlapping tag-based selections (overlap is allowed but generates
   duplicate recovery points).
6. **Region coverage** — for cross-region copy, the destination region
   has a vault with KMS key.
7. **Recovery point presence** — for restore, the recovery point ARN
   exists in the target vault and is `COMPLETED` (not `DELETED` or
   `EXPIRED`).

**Recovery time baselines (2026):**
- Snapshot backup: 5-30 min for EBS, 15-60 min for RDS, depending on
  size.
- Continuous backup (PITR) restore: seconds to minutes for EC2 within
  the 35-day window.
- Cross-region copy: minutes to hours depending on data size and
  inter-region bandwidth.
- Cold (GLACIER) restore: 3-5 hours (Standard), 1-5 min (Expedited),
  5-12 hours (Bulk).

## Mindset

Three AWS Backup realities drive every operation:

- **Compliance mode is irreversible.** Once `PutBackupVaultLockConfiguration`
  is applied with `Mode: COMPLIANCE`, the vault cannot be deleted until
  the retention window expires, and retention can only be lengthened.
  Even the root account cannot bypass it. Treat compliance lock as a
  one-way door — confirm the retention window before applying. The
  `ChangeableForDays` parameter provides a grace window (max 72 hours
  from initial lock) during which the lock can be removed; after that,
  it is permanent.

- **PITR requires continuous backups, not snapshots.** Point-in-time
  recovery for EC2 and RDS requires the backup plan rule to set
  `RecoveryPointTier: CONTINUOUS` (for EC2, via the
  `aws:backup:request-continuous-backup` condition; for RDS, via
  `BackupPlan.AdvancedBackupSettings`). Snapshot-only plans do NOT
  support PITR. Operators frequently enable continuous backups via the
  console without realizing the underlying rule type changed — verify
  via `describe-backup-plan` `Rules[].ContinuousBackup`.

- **Vaults are region-bound.** A backup vault exists in exactly one
  region. Cross-region copy creates a separate recovery point in the
  destination region's vault; it does NOT replicate the vault itself.
  Restoring cross-region requires the destination vault, the
  destination region's KMS key, and the destination IAM permissions.

## Pre-flight: vault/KMS/IAM metadata gate
> Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.


## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious AWS Backup behaviors
> Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks. If ANY fails, verdict is BLOCKED with failures in
PRE_CHECKS. Do NOT execute.

> Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.

Condensed per-operation gate — every branch, one line each (full verbatim listing:
[references/diagnostic-commands.md](references/diagnostic-commands.md)):

- ALL operations: vault name spelled correctly (case-sensitive); vault exists in the same account+region; IAM role holds the required `backup:*` permission.
- create-vault: KMS key ARN exists and `Enabled`; key policy grants `kms:GenerateDataKey` + `kms:Decrypt` to `backup.<region>.amazonaws.com`; vault name not already in use.
- vault lock (COMPLIANCE): not already COMPLIANCE-locked (unless lengthening `MaxRetentionDays`); `MaxRetentionDays` >= longest retention of any plan writing to the vault; `MinRetentionDays` >= oldest recovery point age; `ChangeableForDays` <= 3.
- create-plan: `StartWindowMinutes`/`CompletionWindowMinutes` within service limits; cross-region destination region has a vault with KMS key; `MoveToColdStorageAfterDays` < `DeleteAfterDays`; CRON or `rate()` schedule, timezone UTC.
- create-selection: plan exists; at least one of `ListOfTags`/`Resources`/`Conditions` populated; `RoleArn` exists and is trusted; overlapping tag-based selections = INFO warning, not BLOCKED.
- start-backup (manual): resource ARN exists; backup vault exists and is reachable; IAM role for the selection exists.
- start-restore: recovery point `Status: COMPLETED` and not expired; `Metadata` includes type-specific fields (EC2 `InstanceId`, RDS `NewDBInstanceIdentifier`); cross-region destination IAM verified; PITR continuous backup enabled.
- diagnose: `describe-backup-job` returns the job; `describe-backup-vault` reflects current state; CloudTrail `StartBackupJob`/`StartCopyJob`/`StartRestoreJob` events within last 7 days.

### Step 2: READY — emit operation plan

Emit `VERDICT: READY` with exact CLI sequence + CONFIRM gate:
- Exact AWS CLI command with all flags populated.
- Expected duration (snapshot time, cold-storage restore time).
- Expected side-effects (new recovery point, new restored resource,
  locked vault).
- CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-backup-vault`,
  `put-backup-vault-lock-configuration`,
  `create-backup-plan`, `create-backup-selection`,
  `start-backup-job`, `start-restore-job`,
  `delete-backup-plan`, `delete-backup-selection`), emit CONFIRM prompt.
  Do NOT execute until confirmed.
- Snapshot current state: `describe-backup-vault --backup-vault-name
  <name> --output json > /tmp/<vault>-backup-$(date +%s).json` (for
  lock changes); `list-recovery-points-by-backup-vault` for restore
  inventory.
- Execute the CLI.
- For compliance-mode vault lock, validate the lock is in the grace
  window (`ChangeableForDays`) if the operator wants the option to
  reverse — after grace, the lock is irreversible.

### Step 4: Post-verification — COMPLETED

ALL checks must pass for `COMPLETED`:
1. For create-vault: `describe-backup-vault` returns the new vault
   with `EncryptionKeyArn`, `NumberOfRecoveryPoints: 0`.
2. For lock: `describe-backup-vault` returns `VaultLock.LockState:
   LOCKED` with the expected `Mode`, `MinRetentionDays`,
   `MaxRetentionDays`, `ChangeableForDays`.
3. For plan: `describe-backup-plan` returns the plan with `Rules`
   populated; `BackupPlanArn` returned.
4. For selection: `list-backup-selections --backup-plan-id <id>`
   returns the new selection with `SelectionId`.
5. For start-backup: `describe-backup-job --backup-job-id <id>`
   returns `State: COMPLETED` and `BackupSizeInBytes > 0`; recovery
   point visible in `list-recovery-points-by-backup-vault`.
6. For start-restore: `describe-restore-job --restore-job-id <id>`
   returns `Status: COMPLETED` and `CreatedResourceArn` populated.
7. For PITR enable: `describe-recovery-point` for the resource shows
   `ContinuousBackup` set; verify `get-recovery-point-restore-metadata`
   returns `PITR` enabled metadata.

If ANY verification fails, emit `VERDICT: ERROR` — do not claim COMPLETED.

## Common patterns (boilerplate)

### Create a backup vault with KMS encryption and tags
> Moved verbatim to [references/common-patterns.md](references/common-patterns.md) — load on demand.


### Apply vault lock in COMPLIANCE mode (WORM, immutable)
> Moved verbatim to [references/vault-lock-and-compliance-guide.md](references/vault-lock-and-compliance-guide.md) — load on demand.


### Apply vault lock in GOVERNANCE mode (soft, mutable by privileged)
> Moved verbatim to [references/vault-lock-and-compliance-guide.md](references/vault-lock-and-compliance-guide.md) — load on demand.


### Create a backup plan with schedule, lifecycle, cross-region copy
> Moved verbatim to [references/common-patterns.md](references/common-patterns.md) — load on demand.


### Create a backup selection by tag
> Moved verbatim to [references/common-patterns.md](references/common-patterns.md) — load on demand.


### Start a manual backup job
> Moved verbatim to [references/common-patterns.md](references/common-patterns.md) — load on demand.


### Start a point-in-time restore (PITR)
> Moved verbatim to [references/restore-and-pitr-guide.md](references/restore-and-pitr-guide.md) — load on demand.


### Enable continuous backup for EC2 PITR
> Moved verbatim to [references/restore-and-pitr-guide.md](references/restore-and-pitr-guide.md) — load on demand.


## Diagnostic flows
> Moved verbatim to [references/error-handling.md](references/error-handling.md) — load on demand.


## Output format (per operation)

The response is a single block using the literal labels `OPERATION:`,
`VAULT:`, `VERDICT:`, `PRE_CHECKS:`, `CHECKLIST:`, `STEPS:`,
`POST_VERIFY:`, `STATE:`, and `NOTES:`. The CHECKLIST rows surface the
backup plan config (rule name, schedule, lifecycle, cross-region copy
action) and the recovery point verification status so the operator
sees the full posture in one read. See "STRICT output contract" below
for the enforced shape and worked examples.

```text
OPERATION: <create-vault | lock-vault | create-plan | create-selection | start-backup | start-restore | enable-pitr | diagnose>
VAULT: <vault-name>
VERDICT: READY | BLOCKED | COMPLETED
PRE_CHECKS:
  - [PASS|FAIL] <check description>
CHECKLIST:
  [✓|✗]  Vault lock mode        current: <UNLOCKED | COMPLIANCE | GOVERNANCE>   recommended: <...>
  [✓|✗]  Backup plan rule       current: <rule name, schedule CRON>             recommended: <...>
  [✓|✗]  Lifecycle              current: <MoveToColdStorageAfterDays / DeleteAfterDays>   recommended: <...>
  [✓|✗]  Cross-region copy      current: <none | dest region + vault + lifecycle>         recommended: <...>
  [✓|✗]  KMS encryption         current: <key ARN, KeyState>                                recommended: <...>
  [✓|✗]  Recovery points        current: <N points, latest Status, latest CompletionDate>  recommended: <...>
  [✓|✗]  Selection scope        current: <tag-based | resource ARNs | conditions>           recommended: <...>
STEPS:
  1. CONFIRM: <prompt>
  2. <CLI command with flags populated>
POST_VERIFY:
  - [PASS|FAIL] <verification description>
STATE: <vault lock state, recovery point status, restore job status after apply>
NOTES: <compliance vs governance rationale, retention window, recovery time estimate, cross-region copy caveats>
```

### Worked example — compliance vault with 7-year retention + cross-region DR copy (READY)

The canonical enterprise compliance pattern: a COMPLIANCE-mode locked
vault with 7-year retention (2557 days) and a cross-region copy action
to a DR vault in us-west-2. Copy the shape exactly.

```text
OPERATION: create-plan
VAULT: prod-compliance-vault-7yr
VERDICT: READY
PRE_CHECKS:
  - [PASS] Vault prod-compliance-vault-7yr exists in us-east-1 (NumberOfRecoveryPoints 0)
  - [PASS] Vault currently UNLOCKED (VaultLock.LockState absent) — lock applied in prior step, see NOTES
  - [PASS] Vault lock COMPLIANCE mode verified: MinRetentionDays 90, MaxRetentionDays 2557, ChangeableForDays 0 (past grace)
  - [PASS] KMS key arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-1234-567890abcdef KeyState Enabled, KeyManager CUSTOMER
  - [PASS] KMS key policy grants kms:GenerateDataKey, kms:Decrypt to backup.us-east-1.amazonaws.com
  - [PASS] DR vault dr-compliance-vault exists in us-west-2 with KMS key arn:aws:kms:us-west-2:111111111111:key/efgh5678
  - [PASS] Caller IAM role holds backup:CreateBackupPlan, backup:CreateBackupSelection
  - [PASS] No overlapping tag-based selections for backup=compliance-daily
CHECKLIST:
  [✓]  Vault lock mode        current: COMPLIANCE (MinRetentionDays 90, MaxRetentionDays 2557)   recommended: keep (regulatory mandate CIS 3.6, SOX, HIPAA)
  [✓]  Backup plan rule       current: ComplianceDailyRule, cron(0 5 ? * * *) UTC 05:00 daily    recommended: keep
  [✓]  Lifecycle              current: MoveToColdStorageAfterDays 90, DeleteAfterDays 2557       recommended: keep (7-yr retention: 365.25 × 7 = 2557)
  [✓]  Cross-region copy      current: dest us-west-2 / dr-compliance-vault, DeleteAfterDays 2557   recommended: keep (DR + regulatory archive)
  [✓]  KMS encryption         current: arn:aws:kms:us-east-1:111111111111:key/abcd1234, KeyState Enabled   recommended: keep
  [✗]  Recovery points        current: 0 recovery points (vault newly created)                   recommended: confirm first recovery point COMPLETED within 24h
  [✓]  Selection scope        current: tag-based backup=compliance-daily, env=prod               recommended: keep (auto-enrolls future tagged resources)
STEPS:
  1. CONFIRM: About to create-backup-plan ComplianceDaily-7yr on vault
     prod-compliance-vault-7yr in account 111111111111 region us-east-1.
     This creates a daily backup plan with 90-day warm → cold storage
     transition, 2557-day (7-year) delete, and a cross-region copy to
     dr-compliance-vault in us-west-2 (also 2557-day retention). The
     vault is COMPLIANCE-locked so retention can only lengthen. Proceed?
     (yes/no)
  2. aws backup create-backup-plan --backup-plan '{
       "BackupPlanName": "ComplianceDaily-7yr",
       "Rules": [
         {
           "RuleName": "ComplianceDailyRule",
           "TargetBackupVaultName": "prod-compliance-vault-7yr",
           "ScheduleExpression": "cron(0 5 ? * * *)",
           "StartWindowMinutes": 480,
           "CompletionWindowMinutes": 1440,
           "Lifecycle": {"MoveToColdStorageAfterDays": 90, "DeleteAfterDays": 2557},
           "CopyActions": [
             {
               "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:111111111111:backup-vault:dr-compliance-vault",
               "Lifecycle": {"DeleteAfterDays": 2557}
             }
           ]
         }
       ]
     }'
  3. aws backup create-backup-selection \
       --backup-plan-id "$(aws backup list-backup-plans --query 'BackupPlansList[?BackupPlanName==`ComplianceDaily-7yr`].BackupPlanId' --output text)" \
       --backup-selection '{
         "SelectionName": "compliance-tagged-daily",
         "IamRoleArn": "arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole",
         "ListOfTags": [{"ConditionType": "STRINGEQUALS", "ConditionKey": "backup", "ConditionValue": "compliance-daily"}],
         "Conditions": {"StringEquals": {"aws:ResourceTag/env": "prod"}}
       }'
POST_VERIFY:
  - (pending execution)
  - aws backup describe-backup-plan --backup-plan-id <id> returns Rules[0].RuleName ComplianceDailyRule
  - aws backup describe-backup-plan --backup-plan-id <id> returns Rules[0].CopyActions[0].DestinationBackupVaultArn referencing dr-compliance-vault in us-west-2
  - aws backup list-backup-selections --backup-plan-id <id> returns selection compliance-tagged-daily
  - After first run (~24h): aws backup list-recovery-points-by-backup-vault --backup-vault-name prod-compliance-vault-7yr returns Status COMPLETED, BackupSizeInBytes > 0
STATE: pending — plan and selection will be CREATED within ~30s; first recovery point within 24h (next cron tick)
NOTES:
  - Vault is COMPLIANCE-locked (MaxRetentionDays 2557). The 7-year
    retention is irreversible past the 3-day grace window (already
    expired, ChangeableForDays 0). Retention can only lengthen.
  - Cross-region copy to us-west-2 provides DR; the copy lifecycle also
    uses DeleteAfterDays 2557 so the DR copy honors the same 7-year
    retention. Verify the us-west-2 vault has the same COMPLIANCE lock.
  - Cold storage transition at 90 days: restores from cold take 3-5
    hours (GLACIER Standard). Document the RTO/RPO matrix — operators
    frequently assume cold-storage restores are as fast as warm.
  - Tag-based selection (backup=compliance-daily) auto-enrolls future
    resources; verify weekly via list-protected-resources that the
    expected resource set is enrolled.
```

### Worked example — create vault with KMS encryption (READY)
> Moved verbatim to [references/worked-examples.md](references/worked-examples.md) — load on demand.


### Worked example — diagnose failed backup job (BLOCKED)
> Moved verbatim to [references/worked-examples.md](references/worked-examples.md) — load on demand.


## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening. The CHECKLIST rows surface the backup plan
config (rule name, schedule, lifecycle, cross-region copy action) and
recovery point verification so the operator sees the full posture
in one read.

```text
OPERATION: <create-vault | lock-vault | create-plan | create-selection | start-backup | start-restore | enable-pitr | diagnose>
VAULT: <vault-name>
VERDICT: READY | BLOCKED | COMPLETED
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
CHECKLIST:
  [✓|✗]  Vault lock mode        current: <UNLOCKED | COMPLIANCE | GOVERNANCE>   recommended: <...>
  [✓|✗]  Backup plan rule       current: <rule name, schedule CRON>             recommended: <...>
  [✓|✗]  Lifecycle              current: <MoveToColdStorageAfterDays / DeleteAfterDays>   recommended: <...>
  [✓|✗]  Cross-region copy      current: <none | dest region + vault + lifecycle>         recommended: <...>
  [✓|✗]  KMS encryption         current: <key ARN, KeyState>                                recommended: <...>
  [✓|✗]  Recovery points        current: <N points, latest Status, latest CompletionDate>  recommended: <...>
  [✓|✗]  Selection scope        current: <tag-based | resource ARNs | conditions>           recommended: <...>
STEPS:
  1. CONFIRM: About to <operation> on vault <name> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command with every flag populated — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <vault lock state, recovery point status, restore job status after apply>
NOTES: <compliance-vs-governance rationale, retention window rationale, recovery time estimate, cross-region copy caveats>
```

### FORBIDDEN output patterns

1. **NEVER start with conversational preamble** ("Let me analyze…",
   "Looking at your setup…"). The `OPERATION:` line is the FIRST line,
   always. Use uppercase verdict values only (`READY`, `BLOCKED`,
   `COMPLETED`).

2. **NEVER omit PRE_CHECKS.** Every pre-check must appear with `[PASS]`
   or `[FAIL]` and a specific reason for each failure. A bare
   "PRE_CHECKS: passed" with no per-check rows is a contract violation.

3. **NEVER apply a COMPLIANCE-mode vault lock without surfacing
   `ChangeableForDays` and the irreversibility caveat in NOTES.** The
   CONFIRM gate MUST state the retention window and grace period. After
   grace, the lock is irreversible even for root — the operator must
   know before confirming.

4. **NEVER list a CLI command with placeholder flags in a READY plan.**
   Every flag must be populated with actual values from the input data.
   `<vault-name>`, `<key-arn>`, `<account>` in a READY block is a
   placeholder leak — resolve it or emit BLOCKED.

5. **NEVER claim COMPLETED without every POST_VERIFY line showing
   `[PASS]`.** If any verification fails, emit `VERDICT: ERROR` with the
   failure reason; do not claim COMPLETED.

6. **NEVER omit the CONFIRM gate as the first STEPS entry** for any
   state-changing operation (create-vault, lock-vault, create-plan,
   create-selection, start-backup, start-restore). Executing without
   CONFIRM is a safety violation.

7. **NEVER omit a CHECKLIST row.** All seven rows MUST appear — vault
   lock mode, backup plan rule, lifecycle, cross-region copy, KMS
   encryption, recovery points, selection scope. Use `[✗]` with a reason
   if the item is not yet configured; do not silently drop rows.

8. **NEVER collapse the COMPLIANCE vs GOVERNANCE distinction.** Always
   state the exact `Mode` in CHECKLIST and NOTES. Governance mode does
   NOT meet CIS 3.6, NIST CP-9, or FedRAMP — emitting GOVERNANCE as
   "compliant" is a regulatory misclassification.

## Anti-Patterns — NEVER do these things

- NEVER apply a COMPLIANCE-mode vault lock without explicitly stating the retention window and the 72-hour grace period in the CONFIRM prompt. After grace, the lock is irreversible even for root.
- NEVER confuse compliance mode with governance mode. Governance mode can be removed by a privileged principal — it does NOT meet regulatory requirements (CIS, NIST, FedRAMP). Always set `--mode COMPLIANCE` explicitly when regulatory posture is required.
- NEVER create a backup plan with a lifecycle that deletes recovery points before the destination vault's MinRetentionDays. The plan will fail at delete time, leaving orphaned recovery points that cannot be deleted until the retention window expires.
- NEVER start a restore without verifying the recovery point `Status: COMPLETED` and the destination region's IAM permissions. Restoring from an `EXPIRED` or `DELETED` recovery point fails silently.
- NEVER assume a tag-based backup selection matches existing resources. Verify via `list-protected-resources` that the selection has matching resources; tag-based selections only enroll future resources as they are tagged.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing CLI.
- **Snapshot before lock change:** `describe-backup-vault --output json
  > /tmp/<vault>-backup-$(date +%s).json` — there is no rollback for
  COMPLIANCE-mode locks applied in error (after grace).
- **Verify KMS key accessibility** before any backup or restore
  operation — the `backup.<region>.amazonaws.com` service principal
  must have `kms:GenerateDataKey` and `kms:Decrypt` in the key policy.
- **Prefer tag-based selections** over resource-ARN lists — future
  resources are auto-enrolled.
- **Test restore quarterly** — backups that never test-restored are
  not reliable. Use a non-production vault for restore drills.

## Expert heuristic: COMPLIANCE vs GOVERNANCE vault lock
> Moved verbatim to [references/vault-lock-and-compliance-guide.md](references/vault-lock-and-compliance-guide.md) — load on demand.


## Recent AWS features (2024-2026)
> Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.



## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — expert-heuristic deep dives, Step-0 expert knowledge, recent AWS features
- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples
- [references/error-handling.md](references/error-handling.md) — diagnostic flows and failure remediation
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight metadata gate and per-operation pre-check listings
- [references/common-patterns.md](references/common-patterns.md) — boilerplate CLI patterns (vault create, plan, selection, manual backup)
- [references/restore-and-pitr-guide.md](references/restore-and-pitr-guide.md) — restore and PITR operations (now includes PITR patterns)
- [references/vault-lock-and-compliance-guide.md](references/vault-lock-and-compliance-guide.md) — vault lock and compliance (now includes lock patterns and heuristic)

## Domain

AWS CloudOps / AWS Backup Vault, Plan, and Restore Operations.

## AWS documentation

- **AWS Backup Developer Guide** — https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html
- **Backup Vault Lock** — https://docs.aws.amazon.com/aws-backup/latest/devguide/vaults.html#vault-lock
- **Backup Plans** — https://docs.aws.amazon.com/aws-backup/latest/devguide/about-backup-plans.html
- **Backup Selections** — https://docs.aws.amazon.com/aws-backup/latest/devguide/assigning-resources.html
- **Point-in-Time Recovery for EC2** — https://docs.aws.amazon.com/aws-backup/latest/devguide/continuous-backups.html
- **AWS Backup Search** — https://docs.aws.amazon.com/aws-backup/latest/devguide/search.html
- **AWS Backup for Amazon FSx** — https://docs.aws.amazon.com/fsx/latest/APIReference/Welcome.html
- **AWS Backup API Reference** — https://docs.aws.amazon.com/aws-backup/latest/devguide/api-reference.html
- **AWS CLI backup reference** — https://docs.aws.amazon.com/cli/latest/reference/backup/
- **AWS Backup Compliance** — https://docs.aws.amazon.com/aws-backup/latest/devguide/backup-compliance.html
