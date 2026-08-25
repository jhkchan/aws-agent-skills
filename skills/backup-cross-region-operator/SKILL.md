---
name: backup-cross-region-operator
description: Operates AWS Backup cross-region and cross-account operations — adds cross-region copy rules to backup plans (destination region, KMS, lifecycle), configures cross-account copy via AWS Organizations backup policies, restores from cross-region recovery points (destination IAM, vault, KMS), deploys DR vault locks, and operates the latest features (continuous backups cross-region, Backup Vault Lock cross-region, cross-account restore with external key). Runs deterministic pre-checks (destination vault + KMS, source role grants backup:CopyIntoBackupVault, accounts in same org, recovery point COMPLETED, region opt-in), emits the exact backup:create-backup-plan / start-copy-job / start-restore-job CLI behind a CONFIRM gate, and verifies state post-apply. Emits a verdict (READY | BLOCKED | COMPLETED). Use when adding a DR copy rule, running cross-region restore drills, configuring cross-account backup, locking DR vaults, or enabling continuous cross-region backups.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws backup create-backup-plan, start-copy-job, describe-copy-job, list-copy-jobs, start-restore-job, describe-restore-job, put-backup-vault-lock-configuration, describe-backup-vault, list-recovery-points-by-backup-vault, describe-recovery-point, list-legal-holds, put-backup-vault-access-policy, create-backup-vault (AWS CLI v2, SSO...
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
  when_to_use: Adding cross-region copy rules to backup plans, configuring cross-account backup via Organizations backup policies, restoring from cross-region recovery points, deploying DR vaults with vault lock, enabling continuous backups across regions, or running cross-region restore drills.
  activation_triggers: cross-region copy backup, DR copy backup plan, cross-account backup, AWS Organizations backup policy, cross-region restore, restore from DR region, destination region backup, destination vault backup, backup vault lock cross-region, DR vault compliance, continuous backup cross-region, PITR cross-region, copy action backup plan, external KMS key backup, cross-account restore, backup start-copy-job
  invocation_schema: 'Input: either (a) a cross-region operation intent (add-copy-rule, start-copy, cross-account-enable, start-cross-region-restore, lock-dr-vault, enable-continuous-cross-region, diagnose) with target source vault, destination region, destination vault, KMS key, lifecycle, and resource scope; OR (b) an existing recovery point ARN in the DR region for live-account restore. Output: deterministic OPERATION/VERDICT/PRE_CHECKS/STEPS/ POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Backup, cross-region copy, cross-account backup, DR copy, disaster recovery, backup plan copy action, CopyActions, destination region, destination vault, KMS key, backup vault lock, compliance mode, governance mode, continuous backup cross-region, PITR cross-region, AWS Organizations, backup policy, cross-account restore, external KMS key, backup vault access policy
  tags: aws-backup, storage, operate, cross-region-copy, cross-account, dr, backup-plan, vault-lock, continuous-backup, kms, organizations, restore
---

# Backup Cross-Region Operator

## What this skill does

Executes AWS Backup cross-region and cross-account operations
correctly and safely — adds cross-region copy rules to backup
plans, configures cross-account copy via AWS Organizations backup
policies, restores from cross-region recovery points, deploys DR
vault locks, and enables continuous backups across regions. Runs
deterministic pre-checks before any state-changing CLI, emits the
exact `backup:*` CLI sequence behind a CONFIRM gate, and verifies
cross-region state after apply. Every operation surfaces the
source region, destination region, KMS key ownership (same vs
external account), and the org-mode-vs-standalone posture so the
operator knows what is reversible.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority + copy baselines | Before any operation |
| **§ Mindset** | Region binding, KMS ownership, vault lock cross-region | Understanding the DR model |
| **§ Pre-flight** | Destination vault + KMS + IAM metadata gate | Before executing any CLI |
| **§ Process** | Per-operation planning: copy-rule, start-copy, cross-account, restore, lock-dr, continuous, diagnose | When choosing which operation |
| **§ Common patterns** | Cross-region copy rule, start-copy-job, cross-account via org policy, cross-region restore, DR vault lock | Boilerplate lookup |
| **§ Output format** | Structured output template with VERDICT, COMMANDS, POST_VERIFY | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes | Review before risky operations |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | Pre-checks failed (destination vault missing, KMS disabled, source IAM lacks `backup:CopyIntoBackupVault`, destination not in org, recovery point EXPIRED, region not opt-in) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Operation applied and post-verification passed (copy job COMPLETED, recovery point in destination vault, restore job COMPLETED, DR vault lock reflected, continuous cross-region enabled) | Emit describe output, copy job state, lock state |

**Priority order for pre-checks (all must pass for READY):**

1. **Destination vault exists in destination region** —
   `describe-backup-vault` in the destination region returns the
   vault. Cross-region copy creates a recovery point in the
   destination vault; it does NOT replicate the source vault.
2. **Destination KMS key state** — `kms describe-key` returns
   `Enabled`. Policy must grant `kms:GenerateDataKey` and
   `kms:Decrypt` to `backup.<destination-region>.amazonaws.com`.
3. **Source IAM role permissions** — caller has
   `backup:CopyIntoBackupVault` on destination vault (cross-account),
   `backup:StartCopyJob` on source, `kms:Decrypt` on source KMS.
4. **Recovery point state** — `Status: COMPLETED` (not EXPIRED).
5. **Cross-account organization state** — for cross-account copy,
   destination account is in the same AWS Organization and the
   Organizations backup policy enables cross-account.
6. **Region opt-in** — destination region opt-in and active.
7. **Source vault lock** — `MinRetentionDays` only blocks deletion;
   copy-out is allowed. Destination `MaxRetentionDays` must be >=
   copy rule's `DeleteAfterDays`.
8. **DR vault lock semantics** — destination vault not already in
   COMPLIANCE mode unless lengthening `MaxRetentionDays`.

**Copy baselines (2026):**
- Cross-region copy: minutes to hours depending on size and
  inter-region bandwidth.
- Cross-account copy (org-mode): adds ~5-15% overhead for KMS
  re-encryption and IAM propagation.
- Continuous backup cross-region: 1-second RPO within source
  region; cross-region copy is asynchronous (minutes to hours).
- DR vault lock: active within ~30s; grace window max 3 days.

## Mindset

Three cross-region AWS Backup realities drive every operation:

The three realities (region binding, KMS ownership, Organizations requirement) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when explaining why an operation is BLOCKED.

## Pre-flight: destination vault + KMS + IAM metadata gate

`describe-backup-vault` in the destination region returns the
destination vault metadata. `describe-organization-configuration`
returns the org-mode state.

Live-account pre-flight command listing moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Run these before any state-changing CLI.

**Malformed input:** emit `VERDICT: ERROR` with reason and remediation.

| Attribute | Effect on operation |
|---|---|
| Destination vault missing | BLOCKED. Create the destination vault first. |
| Destination KMS `Disabled` | BLOCKED. Re-enable the key or use a different key. |
| Destination KMS AWS-managed (`aws/backup`) | Works but no cross-account grant. INFO. |
| Source recovery point `EXPIRED` / `DELETED` | BLOCKED. Pick a different recovery point. |
| Source not in same Organization as destination | BLOCKED for cross-account. Same-account cross-region works. |
| Org policy missing cross-account allow | BLOCKED for cross-account. |
| Destination vault in COMPLIANCE lock | Cannot shorten `MaxRetentionDays`. Copy `DeleteAfterDays` must fit. |
| `aws:DisableCrossAccountBackup: true` in org policy | BLOCKED for cross-account. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious cross-region behaviors
Step 0 deep-dive moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when an operation fails for a non-obvious reason.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks. If ANY fails, verdict is BLOCKED. Do NOT execute.

**For ALL operations:**
1. Source and destination regions both opt-in.
2. Caller IAM role holds the required `backup:*` permission.
3. Source vault exists in the source region.

**For add-copy-rule (plan update):**
4. Destination vault exists in destination region.
5. Destination KMS key `Enabled`.
6. `DeleteAfterDays` in `CopyActions[].Lifecycle` fits destination
   vault's `MaxRetentionDays` (if locked).
7. Plan's `Rules[].TargetBackupVaultName` references a valid source.

**For start-copy (manual):**
4. Source recovery point `Status: COMPLETED`.
5. Destination vault exists.
6. Source IAM role holds `backup:StartCopyJob` and (cross-account)
   `backup:CopyIntoBackupVault`.
7. Source KMS policy grants `kms:Decrypt` to source backup role.
8. Destination KMS policy grants `kms:GenerateDataKey`,
   `kms:Decrypt` to `backup.<destination-region>.amazonaws.com`.

**For cross-account-enable:**
4. Caller is Organizations management or delegated admin.
5. Source and destination accounts in same org.
6. `BACKUP_POLICY` service enabled.
7. No `aws:DisableCrossAccountBackup` flag.

**For start-cross-region-restore:**
4. Recovery point exists in destination vault, `Status: COMPLETED`.
5. Destination IAM role holds `backup:StartRestoreJob`,
   `backup:DescribeRestoreJob`.
6. `Metadata` includes resource-type-specific fields (SubnetId,
   SecurityGroupIds for EC2; NewDBInstanceIdentifier for RDS).
7. Destination KMS key grants `kms:Decrypt` to restore role.

**For lock-dr-vault:**
4. Destination vault exists.
5. Not already in COMPLIANCE mode (unless lengthening
   `MaxRetentionDays`).
6. `MaxRetentionDays` >= any existing destination recovery point
   age.
7. `ChangeableForDays` <= 3.

**For enable-continuous-cross-region:**
4. Source plan rule has `ContinuousBackup: true`.
5. Cross-region copy rule in same plan rule.
6. Underlying resource supports continuous backup (EC2, RDS, S3).

**For diagnose:**
5. `describe-copy-job --copy-job-id <id>` returns the job.
6. `list-copy-jobs --region <source>` shows active jobs.
7. `describe-recovery-point` in destination shows copied point.

### Step 2: READY — emit operation plan

Emit `VERDICT: READY` with exact CLI sequence + CONFIRM gate:
- Exact AWS CLI command with all flags populated.
- Expected duration (cross-region copy minutes to hours; restore
  5-60 min depending on resource type).
- Expected side-effects (new recovery point in destination vault,
  new restored resource in destination region, locked DR vault).
- CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-backup-plan` with copy rule, `start-copy-job`,
  `start-restore-job`, `put-backup-vault-lock-configuration`,
  `put-backup-vault-access-policy`), emit CONFIRM prompt. Do NOT
  execute until confirmed.
- Snapshot current state: `describe-backup-vault --output json >
  /tmp/<vault>-xregion-$(date +%s).json` for lock changes;
  `list-recovery-points-by-backup-vault` for copy inventory;
  `describe-organization-configuration` for org-policy changes.
- Execute the CLI.
- For COMPLIANCE-mode DR vault lock, validate the grace window
  (`ChangeableForDays`) if the operator wants reversal option —
  after grace, the lock is irreversible.

### Step 4: Post-verification — COMPLETED

ALL checks must pass for `COMPLETED`:
1. For add-copy-rule: `describe-backup-plan` returns the plan with
   `CopyActions` populated; `BackupPlanArn` returned.
2. For start-copy: `describe-copy-job --copy-job-id <id>` returns
   `State: COMPLETED` and `DestinationRecoveryPointArn`
   populated; recovery point visible in destination vault via
   `list-recovery-points-by-backup-vault --region <destination>`.
3. For cross-account-enable: `organizations
   describe-effective-policy --policy-type BACKUP_POLICY` returns
   the updated policy; first cross-account copy succeeds.
4. For start-cross-region-restore: `describe-restore-job
   --restore-job-id <id>` returns `Status: COMPLETED` and
   `CreatedResourceArn` in destination region.
5. For lock-dr-vault: `describe-backup-vault --region <destination>`
   returns `VaultLock.LockState: LOCKED` with the expected `Mode`,
   `MinRetentionDays`, `MaxRetentionDays`, `ChangeableForDays`.
6. For enable-continuous-cross-region: `describe-backup-plan`
   returns `Rules[].ContinuousBackup: true` and `CopyActions[]`
   populated.

If ANY verification fails, emit `VERDICT: ERROR` — do not claim COMPLETED.

## Common patterns (boilerplate)

### Add a cross-region copy rule to a backup plan

```bash
aws backup create-backup-plan \
  --backup-plan '{
    "BackupPlanName": "prod-daily-with-dr",
    "Rules": [
      {
        "RuleName": "DailyBackup",
        "TargetBackupVaultName": "prod-daily-vault",
        "ScheduleExpression": "cron(0 5 ? * * *)",
        "StartWindowMinutes": 480,
        "CompletionWindowMinutes": 1440,
        "Lifecycle": {"MoveToColdStorageAfterDays": 30, "DeleteAfterDays": 365},
        "CopyActions": [
          {
            "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault",
            "Lifecycle": {"DeleteAfterDays": 90}
          }
        ]
      }
    ]
  }' --region us-east-1
```

The `DestinationBackupVaultArn` references the destination region's
vault ARN. The `Lifecycle` in `CopyActions` is independent of the
source rule's lifecycle.

### Start a manual cross-region copy job

```bash
aws backup start-copy-job \
  --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4 \
  --source-backup-vault-name prod-daily-vault \
  --destination-backup-vault-arn arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
  --idempotency-token "$(date +%s)" \
  --region us-east-1
```

Returns a `CopyJobId`. Poll via `describe-copy-job --copy-job-id
<id>` until `State: COMPLETED`. The destination recovery point
appears in the destination region's vault.

### Configure cross-account backup via Organizations policy
Org policy + destination vault access policy CLI moved to [references/cross-account-and-org-policy-guide.md](references/cross-account-and-org-policy-guide.md).
Load it when enabling cross-account backup.

### Start a cross-region restore
Restore CLI moved to [references/cross-region-restore-and-dr-vault-lock-guide.md](references/cross-region-restore-and-dr-vault-lock-guide.md).
Load it before running start-restore-job in the destination region.

### Apply vault lock on the DR vault (COMPLIANCE mode)
DR vault lock CLI moved to [references/cross-region-restore-and-dr-vault-lock-guide.md](references/cross-region-restore-and-dr-vault-lock-guide.md).
Load it before any COMPLIANCE-mode lock change.

## Diagnostic flows
All three diagnostic flows (copy stuck/failed, restore failed, cross-account InvalidParameterValueException) moved to [references/error-handling.md](references/error-handling.md).
Load it when a copy or restore job fails.

## Output format (per operation)

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

### Worked example — add cross-region copy rule (READY)

```text
OPERATION: add-copy-rule
VERDICT: READY
TARGET: prod-daily-vault (us-east-1) -> dr-vault (us-west-2)
PRE_CHECKS:
  - [PASS] Source vault prod-daily-vault exists in us-east-1
  - [PASS] Destination vault dr-vault exists in us-west-2
  - [PASS] Destination KMS key arn:aws:kms:us-west-2:111111111111:key/xyz
    Enabled, policy grants backup.us-west-2.amazonaws.com
  - [PASS] DeleteAfterDays 90 <= destination MaxRetentionDays 3650
  - [PASS] Caller IAM role holds backup:CreateBackupPlan
STEPS:
  1. CONFIRM: About to add cross-region copy rule to plan
     prod-daily-with-dr in us-east-1. Recovery points will be
     copied to dr-vault in us-west-2 with 90-day retention. Cost
     accrues per-GB-transferred + per-GB-stored. Proceed? (yes/no)
  2. aws backup create-backup-plan --backup-plan '{...}' --region us-east-1
POST_VERIFY:
  - (pending execution)
  - describe-backup-plan returns CopyActions with destination us-west-2
  - First copy job runs at next schedule (cron 0 5 ? * * *)
STATE: pending — plan CREATED within ~10s; first cross-region copy
within 24h
NOTES:
  - Destination vault dr-vault is in us-west-2 — separate from
    source vault prod-daily-vault. Vault locks are independent.
  - Destination KMS key is customer-managed — verify rotation.
  - Cross-region copy creates a NEW recovery point in dr-vault;
    does NOT replicate the source vault.
```

### Worked example — start cross-region copy (READY)
Full example moved to [references/worked-examples.md](references/worked-examples.md).
Load it before emitting a start-copy READY plan.

### Worked example — cross-account copy BLOCKED
Full example moved to [references/worked-examples.md](references/worked-examples.md).
Load it when cross-account pre-checks fail.

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
OPERATION: <add-copy-rule | start-copy | cross-account-enable | start-cross-region-restore | lock-dr-vault | enable-continuous-cross-region | diagnose>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <source-vault / destination-vault / copy-job-id / restore-job-id>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> from <source> in region <src-region> to <destination> in region <dst-region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command with every flag populated — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
STATE: <copy job state, recovery point status in destination, restore job status, vault lock state in destination>
NOTES: <region-binding caveat, KMS ownership rationale, org-mode requirement, inter-region bandwidth estimate, cost impact>
```

### FORBIDDEN output patterns

- NEVER start with conversational preamble ("Let me analyze…") — the VERDICT block is the FIRST line, always. Use uppercase verdict values only (`READY`, `BLOCKED`, `COMPLETED`).
- NEVER omit PRE_CHECKS — every pre-check must appear with `[PASS]` or `[FAIL]` and a specific reason for each failure.
- NEVER attempt cross-account copy without surfacing the same-AWS-Organization requirement and the Organizations backup policy dependency in NOTES.
- NEVER list a CLI command with placeholder flags in a READY plan — every flag must be populated with actual values from the input data.
- NEVER claim COMPLETED without every POST_VERIFY line showing `[PASS]`, and never omit the CONFIRM gate as the first STEPS entry for state-changing operations.

## Anti-Patterns — NEVER do these things

- NEVER assume cross-account copy works with IAM alone. AWS Backup cross-account requires both accounts in the same AWS Organization AND an Organizations `BACKUP_POLICY` enabling the relationship. Standalone cross-account returns `InvalidParameterValueException`.
- NEVER assume a source vault lock prevents copy-out. `MinRetentionDays` only blocks deletion; copy-out is allowed. The destination vault's `MaxRetentionDays` is what caps the copy rule's `DeleteAfterDays` — surface both locks in NOTES.
- NEVER start a cross-region restore in the source region. The `start-restore-job` CLI must be invoked in the destination region where the recovery point lives. Source-region invocation returns `ResourceNotFoundException`.
- NEVER enable continuous backup and assume cross-region PITR. Source-region continuous backup supports 1-second RPO within the region; the cross-region copy is a point-in-time snapshot, NOT a continuous stream. Cross-region PITR requires application-level replication (Aurora Global, DynamoDB global tables).
- NEVER apply a COMPLIANCE-mode DR vault lock without surfacing the destination region, the 72-hour grace window, and the irreversibility caveat in the CONFIRM prompt. Each region's vault lock is independent — locking the source does NOT lock the destination.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing CLI.
- **Snapshot before lock change** (`describe-backup-vault --output
  json > /tmp/<vault>-xregion-$(date +%s).json`) — no rollback for
  COMPLIANCE-mode locks after grace.
- **Verify destination vault + KMS** before any copy or restore.
- **Verify Organizations state** for cross-account operations.
- **Estimate cost** for large cross-region copies.

## Expert heuristic: cross-region vs cross-account
Full heuristic (decision tree, per-resource-type caveats, duration baselines, DR-drill rule) moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when choosing between cross-region and cross-account patterns.

## Recent AWS features (2024-2026)
Feature detail moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when scoping continuous cross-region, external key sharing, or FSx copies.

## References (load on demand)

- [Cross-account and Organizations policy guide](references/cross-account-and-org-policy-guide.md) — org backup policy structure, destination vault access policy, cross-account KMS sharing, common failures
- [Cross-region restore and DR vault lock guide](references/cross-region-restore-and-dr-vault-lock-guide.md) — restore flow, per-resource-type metadata, DR vault lock semantics, continuous backup
- [Worked examples](references/worked-examples.md) — start-copy READY and cross-account BLOCKED worked examples
- [Error handling](references/error-handling.md) — copy-job stuck/failed, restore failed, cross-account InvalidParameterValueException flows
- [Diagnostic commands](references/diagnostic-commands.md) — live-account pre-flight command listing
- [Advanced patterns](references/advanced-patterns.md) — mindset realities, Step 0 expert knowledge, cross-region vs cross-account heuristic, recent AWS features

## Domain

AWS CloudOps / AWS Backup Cross-Region and Cross-Account Operations.

## AWS documentation

- **AWS Backup Developer Guide** — https://docs.aws.amazon.com/aws-backup/latest/devguide/whatisbackup.html
- **Cross-Region Backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/cross-region-backup.html
- **Cross-Account Backup** — https://docs.aws.amazon.com/aws-backup/latest/devguide/cross-account-backup.html
- **Organizations Backup Policy** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_backup.html
- **Backup Vault Lock** — https://docs.aws.amazon.com/aws-backup/latest/devguide/vaults.html#vault-lock
- **Start-Copy-Job** — https://docs.aws.amazon.com/aws-backup/latest/devguide/API_StartCopyJob.html
- **Cross-Region Restore** — https://docs.aws.amazon.com/aws-backup/latest/devguide/restoring-ami.html
- **AWS Backup API Reference** — https://docs.aws.amazon.com/aws-backup/latest/devguide/api-reference.html
- **AWS CLI backup reference** — https://docs.aws.amazon.com/cli/latest/reference/backup/
- **AWS Backup Pricing** — https://aws.amazon.com/backup/pricing/

