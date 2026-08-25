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

- **A backup vault is region-bound.** A vault exists in exactly one
  region. Cross-region copy creates a separate recovery point in
  the destination region's vault; it does NOT replicate the vault
  itself. The destination vault's name, KMS key, and lock
  configuration are independent of the source. Operators often
  assume the source vault's lock applies to the destination — it
  does not.

- **KMS key ownership matters for cross-account.** In same-account
  cross-region copy, the destination region KMS key is owned by
  the same account. In cross-account copy, the destination KMS key
  is owned by the destination account; the source account's
  `backup:StartCopyJob` role must be granted `kms:Decrypt` on the
  source KMS AND the destination account's KMS key policy must
  grant `kms:GenerateDataKey` and `kms:Decrypt` to
  `backup.<destination-region>.amazonaws.com` (and to the source
  account principal for cross-account re-encryption).

- **Cross-account copy requires AWS Organizations.** AWS Backup
  cross-account backup works ONLY when the source and destination
  accounts are in the same AWS Organization, and the Organizations
  backup policy (`backup-policy`) explicitly enables the
  cross-account relationship. Standalone cross-account copy via
  IAM alone is NOT supported — the operation returns
  `InvalidParameterValueException`.

## Pre-flight: destination vault + KMS + IAM metadata gate

`describe-backup-vault` in the destination region returns the
destination vault metadata. `describe-organization-configuration`
returns the org-mode state.

**Live-account pre-flight (skip if offline plan):**
1. `backup describe-backup-vault --backup-vault-name
   <destination-vault> --region <destination-region>` — confirm
   vault exists; capture `EncryptionKeyArn`, `VaultLock`.
2. `kms describe-key --key-id <destination-key-arn> --region
   <destination-region>` — capture `KeyState`, `KeyManager`.
3. `backup describe-backup-vault --backup-vault-name <source-vault>
   --region <source-region>` — source vault lock state.
4. `backup describe-recovery-point --backup-vault-name <source-vault>
   --recovery-point-arn <arn> --region <source-region>` — capture
   recovery point `Status`.
5. `backup list-copy-jobs --region <source-region>` — active jobs.
6. `organizations describe-organization` +
   `describe-effective-policy --policy-type BACKUP_POLICY` —
   org-mode state and cross-account policy.
7. `iam get-role-policy` for the source backup role — verify
   `backup:StartCopyJob`, `backup:CopyIntoBackupVault`,
   `kms:Decrypt` on source key.

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

- **Cross-region copy in a backup plan uses `CopyActions`.** The
  plan's `Rules[].CopyActions[]` array defines destination region,
  vault ARN, and lifecycle in destination. Each rule can have
  multiple `CopyActions` (multi-region DR).
- **`start-copy-job` is the manual alternative to a plan rule.**
  Use for one-off copies (DR drill, audit export). Returns a
  `CopyJobId`.
- **Cross-account copy requires Organizations.** Source and
  destination accounts must be in the same org, with an
  Organizations `BACKUP_POLICY` enabling the relationship. The
  destination vault's access policy must grant
  `backup:CopyIntoBackupVault` to the source account.
- **The destination vault access policy is the gate.** Without
  `backup:CopyIntoBackupVault` for the source account's role, the
  copy job fails with `AccessDeniedException`.
- **Cross-account KMS re-encryption is implicit.** Backup decrypts
  source with source key, re-encrypts with destination key. Both
  key policies must allow `backup.<region>.amazonaws.com` and (for
  cross-account) the source account principal.
- **Continuous backup (PITR) does NOT replicate point-in-time
  across regions.** Source region continuous backup is 1-second
  RPO within region. Cross-region copy is a point-in-time snapshot,
  NOT a continuous stream. Cross-region PITR requires
  application-level replication (Aurora Global, DynamoDB global
  tables).
- **Cross-region restore runs in the destination region.** Invoke
  `start-restore-job` in the destination region where the recovery
  point lives. IAM role and metadata are destination-region-specific.
- **Vault lock in source region does NOT prevent copy-out.**
  `MinRetentionDays` only blocks deletion; copy-out is allowed.
  Destination `MaxRetentionDays` caps the copy rule's
  `DeleteAfterDays`.
- **Copy duration depends on size and bandwidth.** EBS minutes;
  RDS 15-60 min; large EFS hours. Verify via `describe-copy-job`
  before launching restore.
- **Cross-account restore requires external key sharing.** When
  destination owns the recovery point and KMS key, the source
  account needs `kms:Decrypt` on the destination KMS key — via
  policy grant or `kms CreateGrant`.
- **Organizations backup policy is the source of truth for
  cross-account.** Tag-based selection in the org policy applies
  to ALL member accounts.
- **Backup Vault Lock cross-region is per-vault.** Locking the
  source vault does NOT lock the destination. Each region's vault
  must be locked separately.
- **Cross-region copy cost is per-GB-transferred + per-GB-stored.**
  For large frequent copies, consider async replication at the
  application layer (Aurora Global, S3 Cross-Region Replication).

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

```bash
# From the Organizations management account
aws organizations create-policy \
  --name "cross-account-backup" \
  --type BACKUP_POLICY \
  --content '{
    "plans": [{
      "rules": [{
        "rule-name": "rule1",
        "target-backup-vault-name": "central-vault",
        "schedule-expression": "cron(0 5 ? * * *)",
        "start-window-minutes": 480,
        "completion-window-minutes": 1440,
        "copy-actions": [{
          "destination-backup-vault-arn": "arn:aws:backup:us-east-1:222222222222:backup-vault:central-vault",
          "lifecycle": {"delete-after-days": 90}
        }]
      }],
      "selection-list": [{
        "selection-name": "tag-based",
        "iam-role-arn": "arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole",
        "list-of-tags": [{"condition-type": "STRINGEQUALS", "condition-key": "backup", "condition-value": "central"}]
      }]
    }]
  }'
```

Destination account's vault access policy must grant
`backup:CopyIntoBackupVault` to the source account:

```bash
aws backup put-backup-vault-access-policy \
  --backup-vault-name central-vault \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
      "Action": "backup:CopyIntoBackupVault",
      "Resource": "*"
    }]
  }' --region us-east-1
```

### Start a cross-region restore

```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:us-west-2:111111111111:recovery-point:5-6-7-8 \
  --metadata '{"InstanceId":"i-restored-xregion","SubnetId":"subnet-xyz","SecurityGroupIds":"sg-xyz","InstanceType":"t3.medium"}' \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
  --resource-type EC2 \
  --region us-west-2
```

Run the CLI in the destination region (`--region us-west-2`). The
`--metadata` fields are destination-region-specific.

### Apply vault lock on the DR vault (COMPLIANCE mode)

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name dr-vault \
  --changeable-for-days 3 \
  --min-retention-days 30 \
  --max-retention-days 3650 \
  --region us-west-2
```

The lock is independent of the source region's vault lock. After
the 3-day grace, the lock is irreversible.

## Diagnostic flows

### Cross-region copy job stuck or failed

1. `describe-copy-job --copy-job-id <id>` — capture `State`,
   `StatusMessage`, `BackupSizeInBytes`, `SourceRecoveryPointArn`.
2. Common failures:
   - `FAILED: IAM role not authorized` — source role lacks
     `backup:StartCopyJob` or `backup:CopyIntoBackupVault`.
   - `FAILED: Destination vault not found` — vault deleted or
     wrong region.
   - `FAILED: KMS key access denied` — source KMS lacks
     `kms:Decrypt`, or destination KMS lacks `kms:GenerateDataKey`.
   - `RUNNING > 6h` — large snapshot; check EC2 copy bandwidth.
3. CloudTrail: `StartCopyJob`, `CopyJobCompleted` events.
4. Remediation: fix IAM/KMS, re-run with `--idempotency-token`.

### Cross-region restore failed

1. `describe-restore-job --restore-job-id <id>` — capture `Status`,
   `StatusMessage`, `CreatedResourceArn`.
2. Common failures:
   - `FAILED: Invalid metadata` — `--metadata` missing
     destination-region-specific fields (SubnetId, SecurityGroupIds
     in destination region).
   - `FAILED: Insufficient capacity` — destination subnet lacks
     capacity.
   - `FAILED: KMS key inaccessible` — destination-region KMS policy
     blocks `backup:Decrypt`.
3. Re-attempt with corrected metadata in the destination region.

### Cross-account copy returns `InvalidParameterValueException`

1. `organizations describe-effective-policy --policy-type
   BACKUP_POLICY` — verify cross-account enabled.
2. `describe-backup-vault --backup-vault-name <destination>` —
   verify vault exists and access policy grants
   `backup:CopyIntoBackupVault` to source.
3. If accounts NOT in same org, cross-account is unsupported. Use
   same-org accounts or re-archive to a same-account destination
   region.

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

```text
OPERATION: start-copy
VERDICT: READY
TARGET: recovery-point 1-2-3-4 (us-east-1) -> dr-vault (us-west-2)
PRE_CHECKS:
  - [PASS] Source recovery point 1-2-3-4 Status COMPLETED
  - [PASS] Destination vault dr-vault exists in us-west-2
  - [PASS] Source IAM role AWSBackupDefaultServiceRole holds
    backup:StartCopyJob
  - [PASS] Source KMS key grants kms:Decrypt to backup.us-east-1
  - [PASS] Destination KMS key grants kms:GenerateDataKey to
    backup.us-west-2
STEPS:
  1. CONFIRM: About to start-copy-job for recovery point 1-2-3-4
     from prod-daily-vault (us-east-1) to dr-vault (us-west-2).
     Duration: minutes to hours depending on size. Proceed? (yes/no)
  2. aws backup start-copy-job --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4 \
       --source-backup-vault-name prod-daily-vault \
       --destination-backup-vault-arn arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault \
       --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
       --idempotency-token 1723305600 --region us-east-1
POST_VERIFY:
  - (pending execution)
  - describe-copy-job returns State COMPLETED and
    DestinationRecoveryPointArn within minutes to hours
  - list-recovery-points-by-backup-vault --backup-vault-name dr-vault
    --region us-west-2 shows the new recovery point
STATE: pending — copy job COMPLETED within minutes to hours
NOTES:
  - Same-account cross-region copy. KMS re-encryption is implicit.
  - Destination recovery point uses destination KMS key (xyz).
  - Cost: per-GB-transferred + per-GB-stored in us-west-2.
```

### Worked example — cross-account copy BLOCKED

```text
OPERATION: cross-account-enable
VERDICT: BLOCKED
TARGET: account 111111111111 -> account 222222222222 (cross-account)
PRE_CHECKS:
  - [FAIL] Source 111111111111 is NOT in the same AWS Organization
    as destination 222222222222. describe-organization returns
    ManagementAccountId 999999999999; 222222222222 is NOT a member.
  - [PASS] Caller holds organizations:DescribeEffectivePolicy
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
STATE: FAILED — cross-account requires same AWS Organization
NOTES:
  - Remediation: invite 222222222222 to the org, then attach a
    BACKUP_POLICY enabling cross-account. Standalone cross-account
    copy is NOT supported.
  - Alternative: copy to a same-account destination region.
```

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

```
CROSS-REGION (same account, different region)
   ├─ Use create-backup-plan with CopyActions[]
   ├─ Destination vault + KMS in destination region
   ├─ Same AWS account owns both regions
   └─ KMS re-encryption is implicit

CROSS-ACCOUNT (different accounts)
   ├─ Same AWS Organization required
   ├─ Organizations BACKUP_POLICY enables cross-account
   ├─ Destination vault access policy grants
   │   backup:CopyIntoBackupVault to source account
   ├─ Source role holds kms:Decrypt on source key
   ├─ Destination KMS policy grants kms:GenerateDataKey,
   │   kms:Decrypt to backup.<destination-region>.amazonaws.com
   │   AND to source account principal
   └─ IAM alone is NOT sufficient
```

**Per-resource-type cross-region caveats:**

| ResourceType | Cross-region behavior |
|---|---|
| `EC2` | Snapshot copied; restore creates new instance in destination |
| `RDS` | Snapshot copied; restore creates new DB instance |
| `EBS` | Snapshot copied; restore creates new volume |
| `S3` | Versioning backup copied; restore overwrites by version |
| `DynamoDB` | Backup copied; restore replaces table |
| `EFS` | File system copied; restore to new file system |
| `Aurora` | Cluster snapshot copied; restore to new cluster |
| `FSx` | Volume-level copy; filesystem-type-specific restore |

**Copy duration baselines:** EBS minutes; RDS 15-60 min; EFS hours;
FSx 30-120 min; S3 minutes-hours by object count.

ALWAYS pair cross-region copy with a quarterly DR drill — operators
often skip test-restore and discover permission gaps during an incident.

## Recent AWS features (2024-2026)

- **AWS Backup continuous backups cross-region (2025)**: continuous
  backup (PITR) for EC2 supports cross-region copy of the
  continuous recovery point; cross-region PITR still requires
  application-level replication.
- **Backup Vault Lock cross-region (2024)**: each region's vault
  lock is independent; the source region's lock does NOT apply to
  the destination region's vault. Locking the DR vault requires
  explicit `put-backup-vault-lock-configuration` in the
  destination region.
- **Cross-account backup via AWS Organizations (2023, refined
  2025)**: Organizations `BACKUP_POLICY` enables cross-account
  backup and restore; supports tag-based selection across member
  accounts; requires `backup:CopyIntoBackupVault` grant on the
  destination vault.
- **AWS Backup external key sharing (2024)**: cross-account
  restore with destination-owned KMS keys via KMS key policy or
  `kms CreateGrant`; supports air-gapped recovery patterns.
- **AWS Backup for Amazon FSx cross-region (2024)**: cross-region
  copy for FSx for Windows File Server, Lustre, OpenZFS, and
  NetApp ONTAP.
- **AWS Backup Audit Manager cross-region (2025)**: cross-region
  audit reporting and compliance frameworks.

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
