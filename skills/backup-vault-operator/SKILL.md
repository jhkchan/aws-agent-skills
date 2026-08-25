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

Run before classification. `describe-backup-vault` returns the full
vault metadata including `VaultLock`, `EncryptionKeyArn`, `NumberOfRecoveryPoints`.
`list-backup-vaults` returns up to 100/page (use `--next-token`).

**Live-account pre-flight (skip if offline plan):**
1. `backup describe-backup-vault --backup-vault-name <name>` — confirm
   vault exists, capture `EncryptionKeyArn`, `VaultLock`, `CreationDate`,
   `NumberOfRecoveryPoints`.
2. `kms describe-key --key-id <key-arn>` — capture `KeyState` and
   `KeyManager` (must be `Enabled` and `AWS` or `CUSTOMER`).
3. `backup list-backup-vaults` — cross-reference vault list.
4. `backup list-recovery-points-by-backup-vault --backup-vault-name <name>`
   — capture recovery points for restore operations; verify the target
   recovery point is `Status: COMPLETED`.
5. `backup list-backup-plans` + `list-backup-selections` — capture
   current plans and selections, check for overlap.
6. `backup describe-backup-job --backup-job-id <id>` — for diagnose
   operations on a specific job.

**Malformed input:** emit `VERDICT: ERROR` with reason and remediation.

| Attribute | Effect on operation |
|---|---|
| `VaultLock.LockState: LOCKED` (compliance) | Retention cannot be shortened; vault cannot be deleted. Plan must respect the existing `MaxRetentionDays`. |
| `VaultLock.LockState: LOCKED` (governance) | Lock can be removed by privileged principal — treat as soft but warn in NOTES. |
| `VaultLock.ChangeableForDays > 0` | Vault is in the grace window — lock can still be modified or removed. Surface explicitly. |
| `KeyState: Disabled` / `PendingDeletion` | KMS key unusable for new backups. BLOCKED. |
| `EncryptionKeyArn` unset | Default AWS-managed key (`aws/backup`) used. Surface as finding for compliance requirements. |
| `NumberOfRecoveryPoints: 0` | Restore not possible. BLOCKED. |
| Overlapping tag-based selections | Allowed but generates duplicate recovery points (and cost). Surface as INFO. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious AWS Backup behaviors

- **Compliance mode is irreversible after `ChangeableForDays` expires.**
  The grace window is set when the lock is applied (max 3 days). During
  grace, the lock can be removed by the principal that created it;
  after grace, no one (including root) can remove the lock or shorten
  retention.
- **Governance mode is soft-bypassable.** Any principal with
  `backup:DeleteBackupVaultLockConfiguration` and
  `iam:CreatePolicy`/`AttachRolePolicy` can remove the lock. For
  regulatory compliance (CIS Benchmark 3.6, NIST 800-53 CP-9), use
  compliance mode.
- **Retention window applies to ALL recovery points in the vault.**
  The vault lock's `MinRetentionDays` and `MaxRetentionDays` constrain
  every recovery point in the vault. The backup plan's lifecycle moves
  recovery points to cold storage or deletes them; the vault lock sets
  the floor (MinRetentionDays) and ceiling (MaxRetentionDays).
- **Tag-based selections apply to future resources.** A selection with
  `Conditions: {"StringEquals": {"aws:ResourceTag/backup": "daily"}}`
  picks up any new resource tagged `backup=daily`. Resource-tag-based
  selection is the recommended pattern; resource-ARN lists are static.
- **Cross-region copy needs a destination vault + KMS.** The copy
  rule in the backup plan references a destination region; AWS Backup
  creates the recovery point in the destination region's default vault
  unless a `BackupVaultName` is specified.
- **Continuous backup (PITR) requires the underlying service to support
  it.** EC2 PITR requires `aws:ec2:enable-point-in-time-recovery` on
  the instance. RDS PITR requires `BackupPlan.AdvancedBackupSettings`
  with `BackupOptions: {"WindowsVSS": "enabled"}` for Windows instances.
- **Backup selection with no `Conditions` and no `ListOfTags` selects
  nothing.** The selection MUST include at least one of `ListOfTags`,
  `Resources`, or `Conditions`. Empty selection silently matches no
  resources.
- **Restore creates a new resource by default.** The original resource
  is NOT overwritten. For RDS, the restore creates a new DB instance
  with a new endpoint; for EC2, a new instance with a new IP (unless
  the restore specifies the original private IP and that IP is
  available).
- **`StartRestoreJob` requires `Metadata` for resource-type-specific
  parameters.** EC2 restore needs `InstanceId`, `SubnetId`,
  `SecurityGroupIds`, `InstanceType`. RDS restore needs
  `NewDBInstanceIdentifier`. Wrong metadata = validation error or
  silent wrong configuration.
- **Backup Vault Lock applies to the vault, NOT to the plan.** Two
  plans writing to the same locked vault share the retention window.
  Cannot have one plan with 30-day retention and another with 7-day
  retention to the same locked vault — MinRetentionDays wins.
- **`Backup Search` (2025) searches across recovery points without
  restoring.** Use `backup search:SearchResource` (or the console
  Backup Search) to find files/items within EBS snapshots, S3 backups,
  and EFS backups without launching a restore job.
- **FSx backups are volume-level.** AWS Backup supports FSx for
  Windows File Server, Lustre, OpenZFS, and NetApp ONTAP. Each
  filesystem type has different restore semantics (volume-level vs
  file-level).
- **Cold storage transition (GLACIER / DEEP_ARCHIVE) is one-way for
  recovery speed.** Restore from GLACIER is 3-5 hours; from DEEP
  ARCHIVE is 12+ hours. Plan the lifecycle transition carefully —
  regulatory archives go to DEEP ARCHIVE, operational recovery stays
  in WARM.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL pre-checks. If ANY fails, verdict is BLOCKED with failures in
PRE_CHECKS. Do NOT execute.

**For ALL operations:**
1. Vault name spelled correctly (case-sensitive).
2. Vault exists in the same account+region as the operation
   (`describe-backup-vault` returns it).
3. IAM role holds the required `backup:*` permission.

**For create-vault:**
4. KMS key ARN exists and is `Enabled`.
5. KMS key policy grants
   `kms:GenerateDataKey`, `kms:Decrypt` to
   `backup.<region>.amazonaws.com`.
6. Vault name not already in use.

**For vault lock (compliance mode):**
4. Vault is not already in compliance mode (`VaultLock.LockState !=
   LOCKED` with `Mode: COMPLIANCE`) unless the operation is to
   lengthen `MaxRetentionDays`.
5. `MaxRetentionDays` is greater than or equal to the longest
   retention in any plan writing to the vault.
6. `MinRetentionDays` is greater than or equal to the longest current
   recovery point age in the vault (else existing points cannot be
   deleted on the existing schedule).
7. `ChangeableForDays` <= 3 (max grace window).

**For create-plan:**
4. At least one rule has `StartWindowMinutes` and `CompletionWindowMinutes`
   within service limits.
5. Cross-region copy destination region has a vault with KMS key.
6. Lifecycle `MoveToColdStorageAfterDays` < `DeleteAfterDays` (cannot
   delete before moving to cold).
7. Schedule uses CRON or simple `rate()`. Verify timezone is UTC.

**For create-selection:**
4. Plan exists (`list-backup-plans` returns the plan ID).
5. At least one of `ListOfTags`, `Resources`, `Conditions` is
   populated (empty selection matches nothing).
6. IAM role `RoleArn` exists and has
   `backup:StartBackupJob` / `backup:PutBackupVaultNotifications`
   trust.
7. No overlapping tag-based selections (INFO-level warning, not
   BLOCKED).

**For start-backup (manual):**
4. Resource ARN exists.
5. Backup vault exists and is reachable.
6. IAM role for the selection exists.

**For start-restore:**
4. Recovery point exists in the target vault and `Status: COMPLETED`.
5. Recovery point is not expired (within retention window).
6. `Metadata` includes resource-type-specific fields (InstanceId for
   EC2, NewDBInstanceIdentifier for RDS).
7. For cross-region restore: destination region IAM permissions
   verified.
8. For PITR: continuous backup is enabled on the resource
   (`describe-recovery-point --backup-vault-name <vault>
   --recovery-point-arn <arn>` shows `IsEncrypted: true` and
   `ResourceType` continuous-capable, plus `CalculatedLifecycle`
   reflects continuous backup window).

**For diagnose operations:**
5. `describe-backup-job --backup-job-id <id>` returns the job.
6. `describe-backup-vault --backup-vault-name <name>` reflects current
   state.
7. CloudTrail `StartBackupJob`, `StartCopyJob`, `StartRestoreJob`
   events within last 7 days for the resource.

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

```bash
aws backup create-backup-vault \
  --backup-vault-name "prod-daily-vault" \
  --encryption-key-arn arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-1234-567890abcdef \
  --creator-request-id "$(date +%s)" \
  --tags Environment=prod,Owner=platform-team
```

Use `--creator-request-id` for idempotency — re-running with the same
ID returns the existing vault without error.

### Apply vault lock in COMPLIANCE mode (WORM, immutable)

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "prod-compliance-vault" \
  --changeable-for-days 3 \
  --min-retention-days 30 \
  --max-retention-days 3650
```

The `--changeable-for-days 3` grace window allows reversing for 72
hours. After that, the lock is permanent. COMPLIANCE mode is the
default; `--mode` flag exists for explicit governance mode.

### Apply vault lock in GOVERNANCE mode (soft, mutable by privileged)

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "prod-governance-vault" \
  --mode GOVERNANCE \
  --min-retention-days 30 \
  --max-retention-days 365
```

Governance mode can be removed by a principal with
`backup:DeleteBackupVaultLockConfiguration`. Not suitable for
regulatory compliance.

### Create a backup plan with schedule, lifecycle, cross-region copy

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
  }'
```

`ScheduleExpression` is in UTC. `StartWindowMinutes` must be less than
`CompletionWindowMinutes`. The `CopyActions` array defines the
cross-region copy with a separate lifecycle in the destination region.

### Create a backup selection by tag

```bash
aws backup create-backup-selection \
  --backup-plan-id "$(aws backup list-backup-plans --query 'BackupPlansList[?BackupPlanName==`prod-daily-with-dr`].BackupPlanId' --output text)" \
  --backup-selection '{
    "SelectionName": "prod-tagged-daily",
    "IamRoleArn": "arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole",
    "ListOfTags": [{"ConditionType": "STRINGEQUALS", "ConditionKey": "backup", "ConditionValue": "daily"}],
    "Conditions": {
      "StringEquals": {"aws:ResourceTag/environment": "prod"},
      "StringNotEquals": {"aws:ResourceTag/criticality": "dev"}
    }
  }'
```

Use `ListOfTags` for forward-compatible selections (new resources
tagged `backup=daily` automatically enroll). Use `Resources` for
static ARN lists. `Conditions` supports `StringEquals`,
`StringLike`, `StringNotEquals` on `aws:ResourceTag/*`.

### Start a manual backup job

```bash
aws backup start-backup-job \
  --backup-vault-name "prod-daily-vault" \
  --resource-arn arn:aws:ec2:us-east-1:111111111111:instance/i-0123456789abcdef0 \
  --iam-role-arn "arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole" \
  --idempotency-token "$(date +%s)" \
  --start-window-minutes 60 \
  --complete-window-minutes 1440 \
  --lifecycle '{"MoveToColdStorageAfterDays": 30, "DeleteAfterDays": 365}'
```

### Start a point-in-time restore (PITR)

```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4 \
  --metadata '{"InstanceId": "i-0 restored", "SubnetId": "subnet-abc123", "SecurityGroupIds": "sg-abc123", "InstanceType": "t3.medium"}' \
  --iam-role-arn "arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole" \
  --resource-type EC2
```

The `--metadata` fields vary by `--resource-type`. For RDS, use
`{"NewDBInstanceIdentifier": "restored-db"}`. For EBS, use
`{"VolumeId": "vol-..."}`. Use
`aws backup get-recovery-point-restore-metadata --recovery-point-arn
<arn>` to get the template metadata for the recovery point.

### Enable continuous backup for EC2 PITR

Continuous backup is set in the backup plan rule via
`advanced backup settings` and the rule's continuous flag:

```bash
aws backup create-backup-plan \
  --backup-plan '{
    "BackupPlanName": "prod-ec2-pitr",
    "Rules": [
      {
        "RuleName": "ContinuousBackup",
        "TargetBackupVaultName": "prod-daily-vault",
        "ScheduleExpression": "cron(0 5 ? * * *)",
        "StartWindowMinutes": 60,
        "CompletionWindowMinutes": 1440,
        "ContinuousBackup": true
      }
    ],
    "AdvancedBackupSettings": [
      {"ResourceType": "EC2", "BackupOptions": {"WindowsVSS": "enabled"}}
    ]
  }'
```

EC2 PITR allows restoring to any 1-minute point within the past 35
days. Verify via `describe-recovery-point` that `ContinuousBackup:
true`.

## Diagnostic flows

### Backup job failed or stuck

1. `describe-backup-job --backup-job-id <id>` — capture `State`,
   `StatusMessage`, `PercentDone`, `CreatedBy`, `BackupType`.
2. Common failures:
   - `FAILED: IAM role not authorized` — the
     `AWSBackupDefaultServiceRole` lacks
     `ec2:CreateTags`, `ec2:DescribeVolumes`,
     `kms:GenerateDataKey`, or service-specific permissions.
   - `FAILED: Resource not found` — the resource was deleted between
     the schedule trigger and execution.
   - `ABORTED: Completion window exceeded` — large resource; increase
     `CompletionWindowMinutes` or use parallel backup.
   - `EXPIRED: Recovery point expired` — retention window passed
     before the backup completed.
3. CloudTrail: `StartBackupJob`, `BackupJobCompleted` events to
   correlate with the IAM role snapshot.
4. Remediation: fix the IAM role / increase windows / snapshot
   offline; re-run `start-backup-job` with `--idempotency-token`.

### Restore job failed

1. `describe-restore-job --restore-job-id <id>` — capture `Status`,
   `StatusMessage`, `CreatedResourceArn`.
2. Common failures:
   - `FAILED: Invalid metadata` — `--metadata` missing required
     fields (SubnetId for EC2, NewDBInstanceIdentifier for RDS).
   - `FAILED: Insufficient capacity` — destination subnet/AZ lacks
     capacity for the restore.
   - `FAILED: KMS key inaccessible` — destination region KMS key
     policy blocks `backup:Decrypt`.
3. Re-attempt with corrected metadata via `start-restore-job` with a
   new `--idempotency-token`.

### Vault lock cannot be removed

1. `describe-backup-vault --backup-vault-name <vault>` — capture
   `VaultLock.LockState`, `Mode`, `ChangeableForDays`.
2. If `Mode: COMPLIANCE` and `ChangeableForDays: 0`, the lock is
   permanent. Surface to operator; cannot be removed.
3. If `Mode: GOVERNANCE`, the lock can be removed by a principal with
   `backup:DeleteBackupVaultLockConfiguration`.

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

```text
OPERATION: create-vault
VAULT: prod-daily-vault
VERDICT: READY
PRE_CHECKS:
  - [PASS] Vault name prod-daily-vault not already in use
  - [PASS] KMS key arn:aws:kms:us-east-1:111111111111:key/abcd1234
    KeyState Enabled, KeyManager CUSTOMER
  - [PASS] KMS key policy grants kms:GenerateDataKey, kms:Decrypt to
    backup.us-east-1.amazonaws.com
  - [PASS] Caller IAM role holds backup:CreateBackupVault
CHECKLIST:
  [✓]  Vault lock mode        current: UNLOCKED (new vault)                       recommended: apply COMPLIANCE lock separately (CIS 3.6) if regulatory
  [✗]  Backup plan rule       current: none (vault newly created)                 recommended: create plan with daily cron(0 5 ? * * *)
  [✗]  Lifecycle              current: none                                       recommended: MoveToColdStorageAfterDays 30, DeleteAfterDays 365 (adjust to mandate)
  [✗]  Cross-region copy      current: none                                       recommended: add CopyAction to dr-vault in us-west-2 if DR required
  [✓]  KMS encryption         current: arn:aws:kms:us-east-1:111111111111:key/abcd1234, KeyState Enabled   recommended: keep
  [✗]  Recovery points        current: 0 (new vault)                              recommended: confirm first recovery point COMPLETED within 24h of first plan run
  [✗]  Selection scope        current: none                                       recommended: tag-based selection backup=daily (auto-enrolls future resources)
STEPS:
  1. CONFIRM: About to create-backup-vault prod-daily-vault in account
     111111111111 region us-east-1. This will CREATE a new vault
     encrypted with KMS key abcd1234. The vault has no lock initially —
     apply lock-vault separately for WORM compliance. Proceed? (yes/no)
  2. aws backup create-backup-vault --backup-vault-name prod-daily-vault \
       --encryption-key-arn arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-1234-567890abcdef \
       --creator-request-id 1723305600 \
       --tags Environment=prod,Owner=platform-team
POST_VERIFY:
  - (pending execution)
  - aws backup describe-backup-vault --backup-vault-name prod-daily-vault returns EncryptionKeyArn set, NumberOfRecoveryPoints 0
STATE: pending — vault will be CREATED within ~30s
NOTES:
  - No vault lock applied. For compliance (CIS Benchmark 3.6), apply
    COMPLIANCE mode lock separately with MinRetentionDays >= 30.
  - KMS key is customer-managed — verify rotation is enabled via
    aws kms get-key-rotation-status --key-id abcd1234.
  - Tags Environment=prod, Owner=platform-team propagate to the vault
    for cost allocation and access control.
```

### Worked example — diagnose failed backup job (BLOCKED)

```text
OPERATION: diagnose
VAULT: prod-daily-vault
VERDICT: BLOCKED
PRE_CHECKS:
  - [PASS] describe-backup-job returns the job (State FAILED,
    ResourceType EC2, BackupSizeInBytes 0)
  - [FAIL] IAM role AWSBackupDefaultServiceRole lacks ec2:CreateTags:
    CloudTrail shows AWSBackupServiceRole assumed at 2026-08-09T05:00:12Z
    attempting ec2:CreateTags on i-0123456789abcdef0 and receiving
    AccessDenied. The role policy includes ec2:CreateVolume,
    ec2:DescribeVolumes but not ec2:CreateTags. AWS Backup requires
    ec2:CreateTags on the snapshot.
  - [PASS] KMS key abcd1234 KeyState Enabled
CHECKLIST:
  [✓]  Vault lock mode        current: GOVERNANCE (soft lock)                     recommended: keep (operational policy, not regulatory)
  [✓]  Backup plan rule       current: DailyBackup, cron(0 5 ? * * *)              recommended: keep
  [✓]  Lifecycle              current: MoveToColdStorageAfterDays 30, DeleteAfterDays 365   recommended: keep
  [✗]  Cross-region copy      current: none                                       recommended: add CopyAction to dr-vault (single-region vault is a DR gap)
  [✓]  KMS encryption         current: arn:aws:kms:us-east-1:111111111111:key/abcd1234, KeyState Enabled   recommended: keep
  [✗]  Recovery points        current: 14 points, latest FAILED (job abc123)      recommended: remediate IAM, re-run with idempotency token
  [✓]  Selection scope        current: tag-based backup=daily, env=prod           recommended: keep
STEPS: (none — pre-checks failed; this is a diagnosis)
POST_VERIFY: (none)
STATE: FAILED — IAM role missing ec2:CreateTags permission
NOTES:
  - Remediation: add ec2:CreateTags, ec2:DeleteTags, ec2:DescribeTags to
    the AWSBackupDefaultServiceRole policy.
  - Re-run the backup with idempotency:
    aws backup start-backup-job --backup-vault-name prod-daily-vault \
      --resource-arn arn:aws:ec2:us-east-1:111111111111:instance/i-0123456789abcdef0 \
      --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
      --idempotency-token "$(date +%s)"
```

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

```
COMPLIANCE MODE
   ├─ Regulatory requirement (CIS, NIST, FedRAMP, SOX, HIPAA)?
   │    └─ YES → COMPLIANCE mode
   │         • MinRetentionDays set to regulatory minimum (>= 90 for HIPAA)
   │         • MaxRetentionDays set to data-retention policy ceiling
   │         • ChangeableForDays 3 (max grace for rollback window)
   │         • Lock cannot be removed by root after grace
   ├─ Operational policy (no regulatory mandate)?
   │    └─ GOVERNANCE mode
   │         • MinRetentionDays set to operational minimum
   │         • Lock can be removed by privileged principal
   │         • Suitable for internal controls, NOT for audit
```

**Per-service backup semantic differences:**

| Service / ResourceType | What to check |
|---|---|
| `EC2` instance | Continuous backup enabled for PITR; WindowsVSS for Windows instances; restore creates new instance (new IP) |
| `RDS` DB instance | PITR requires `AdvancedBackupSettings.BackupOptions.WindowsVSS=enabled` for Windows; restore creates new DB instance (new endpoint) |
| `EBS` volume | Snapshot-only; restore creates new volume (must detach/attach original) |
| `S3` bucket | Versioning must be enabled; restore overwrites by version, not by replace |
| `DynamoDB` table | Continuous backup (PITR) is the native option; AWS Backup adds cross-region copy |
| `EFS` file system | Incremental; restore to new file system or item-level via Backup Search |
| `FSx` Windows / Lustre / OpenZFS / ONTAP | Volume-level restore; filesystem-level differs by type |
| `Aurora` cluster | Cluster-level PITR via `aws:backup:request-continuous-backup`; restore to new cluster |

**Cold-storage transition policy:**
- WARM (default): immediate restore, no extra cost. Use for
  operational recovery.
- COLD (GLACIER): 3-5 hour restore. Use for archives accessed monthly.
- ARCHIVE (DEEP_ARCHIVE): 12+ hour restore. Use for multi-year
  compliance archives.

ALWAYS pair cold storage with a documented RTO/RPO matrix — operators
frequently assume cold-storage recovery points restore as fast as
warm, then discover 3+ hour waits during incidents.

## Recent AWS features (2024-2026)

- **AWS Backup for Amazon FSx** (2025): backup and restore for FSx
  for Lustre, OpenZFS, and NetApp ONTAP with volume-level granularity.
- **AWS Backup Search** (2025): search across recovery points for
  files (EFS, S3) and items (DynamoDB, RDS) without launching a
  restore job; supports item-level restore from search results.
- **Continuous backups for EC2** (2024): point-in-time recovery for
  EC2 instances within a 35-day window; the backup plan rule must set
  `ContinuousBackup: true`.
- **AWS Backup support for Amazon S3** (2024): continuous backup with
  PITR for S3 objects; versioning and Object Lock requirements.
- **Backup Vault Lock grace window refinement**: max 3 days
  `ChangeableForDays`; clarified that governance mode does NOT meet
  regulatory compliance.
- **Cross-account backup** (2023, refined 2025): backup and restore
  across AWS accounts via AWS Organizations; requires
  `backup:CrossAccountBackupRole` delegation.
- **AWS Backup for Amazon Timestream, Amazon Neptune, and Amazon
  MQ** (2024): expanded service coverage.

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
