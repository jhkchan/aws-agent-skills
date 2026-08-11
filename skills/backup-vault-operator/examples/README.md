# End-to-end usage scenario: backup-vault-operator

A walkthrough showing the skill creating a production backup vault
with KMS encryption, applying a COMPLIANCE-mode vault lock for
regulatory compliance, authoring a backup plan with cross-region DR
copy, and starting a PITR restore drill.

## Input (user prompt)

> Create a backup vault `prod-compliance-vault` in us-east-1 encrypted
> with KMS key `arn:aws:kms:us-east-1:111111111111:key/abcd1234`.
> Apply a COMPLIANCE-mode vault lock with MinRetentionDays=30,
> MaxRetentionDays=3650, ChangeableForDays=3 (for CIS Benchmark 3.6).
> Then create a backup plan `prod-daily-with-dr` that backs up the
> vault nightly at 05:00 UTC, transitions to cold storage at 30 days,
> deletes at 365 days, and copies to a DR vault in us-west-2. Finally,
> start a PITR restore for an EC2 instance from a recovery point in
> the vault.

## Skill output — create-vault

```text
OPERATION: create-vault
VERDICT: READY
TARGET: prod-compliance-vault
PRE_CHECKS:
  - [PASS] Vault name prod-compliance-vault not already in use
  - [PASS] KMS key abcd1234 KeyState Enabled, KeyManager CUSTOMER
  - [PASS] KMS key policy grants kms:GenerateDataKey, kms:Decrypt to
    backup.us-east-1.amazonaws.com
  - [PASS] Caller IAM role holds backup:CreateBackupVault
STEPS:
  1. CONFIRM: About to create-backup-vault prod-compliance-vault in
     account 111111111111 region us-east-1. This will CREATE a new
     vault encrypted with KMS key abcd1234. Proceed? (yes/no)
  2. aws backup create-backup-vault --backup-vault-name prod-compliance-vault \
       --encryption-key-arn arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-1234-567890abcdef \
       --creator-request-id 1723305600 \
       --tags Environment=prod,Owner=platform-team
POST_VERIFY:
  - describe-backup-vault returns the vault with EncryptionKeyArn set
    and NumberOfRecoveryPoints 0
STATE: pending — CREATED within ~30s
NOTES:
  - No vault lock applied. Apply lock-vault separately for compliance.
```

## Skill output — lock-vault (COMPLIANCE mode)

```text
OPERATION: lock-vault
VERDICT: READY
TARGET: prod-compliance-vault
PRE_CHECKS:
  - [PASS] Vault prod-compliance-vault exists in us-east-1
  - [PASS] Vault currently UNLOCKED
  - [PASS] MinRetentionDays 30 <= MaxRetentionDays 3650
  - [PASS] ChangeableForDays 3 <= 3 max grace
STEPS:
  1. CONFIRM: About to apply COMPLIANCE-mode lock on
     prod-compliance-vault. After the 72-hour grace window, the lock
     CANNOT be removed even by root. Proceed? (yes/no)
  2. aws backup put-backup-vault-lock-configuration \
       --backup-vault-name prod-compliance-vault \
       --changeable-for-days 3 --min-retention-days 30 --max-retention-days 3650
POST_VERIFY:
  - describe-backup-vault returns VaultLock.LockState LOCKED, Mode
    COMPLIANCE, MinRetentionDays 30, MaxRetentionDays 3650,
    ChangeableForDays 3
STATE: pending — lock active within ~30s; grace window starts
NOTES:
  - COMPLIANCE mode for CIS Benchmark 3.6 / NIST CP-9. After grace,
    lock is irreversible. Use ChangeableForDays 3 for a 72-hour
    reversal window.
```

## Skill output — create-plan with cross-region copy

```text
OPERATION: create-plan
VERDICT: READY
TARGET: prod-daily-with-dr
PRE_CHECKS:
  - [PASS] Vault prod-compliance-vault exists
  - [PASS] DR vault arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault
    exists in destination region
  - [PASS] MoveToColdStorageAfterDays 30 < DeleteAfterDays 365
  - [PASS] DeleteAfterDays 365 <= MaxRetentionDays 3650 (vault lock ceiling)
STEPS:
  1. CONFIRM: About to create-backup-plan prod-daily-with-dr with
     nightly backups at 05:00 UTC, cold storage at 30d, delete at
     365d, DR copy to us-west-2. Proceed? (yes/no)
  2. aws backup create-backup-plan --backup-plan '{
       "BackupPlanName": "prod-daily-with-dr",
       "Rules": [{
         "RuleName": "DailyBackup",
         "TargetBackupVaultName": "prod-compliance-vault",
         "ScheduleExpression": "cron(0 5 ? * * *)",
         "StartWindowMinutes": 480,
         "CompletionWindowMinutes": 1440,
         "Lifecycle": {"MoveToColdStorageAfterDays": 30, "DeleteAfterDays": 365},
         "CopyActions": [{
           "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault",
           "Lifecycle": {"DeleteAfterDays": 90}
         }]
       }]
     }'
POST_VERIFY:
  - describe-backup-plan returns the plan with Rules populated
  - BackupPlanArn set; CrossRegionCopyAction populated for us-west-2
STATE: pending — plan CREATED within ~10s; first backup at next 05:00 UTC
NOTES:
  - Cross-region copy creates a separate recovery point in us-west-2
    dr-vault. The DR copy lifecycle (DeleteAfterDays 90) is
    independent of the source (365 days). Both must respect the
    destination vault's lock (if any).
```

## Skill output — start-restore (PITR)

```text
OPERATION: start-restore
VERDICT: READY
TARGET: arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4
PRE_CHECKS:
  - [PASS] Recovery point exists in prod-compliance-vault
  - [PASS] Status COMPLETED
  - [PASS] ContinuousBackup true (PITR-capable)
  - [PASS] RestoreTime 2026-08-09T14:30:00Z within 35-day continuous
    window
  - [PASS] Metadata SubnetId, SecurityGroupIds, InstanceType populated
  - [PASS] IAM role AWSBackupDefaultServiceRole holds ec2:RunInstances
STEPS:
  1. CONFIRM: About to start-restore-job for EC2 instance to
     RestoreTime 2026-08-09T14:30:00Z. This will CREATE a new EC2
     instance i-restored-pitr in subnet-abc123. Proceed? (yes/no)
  2. aws backup start-restore-job \
       --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4 \
       --metadata '{"InstanceId":"i-restored-pitr","SubnetId":"subnet-abc123","SecurityGroupIds":"sg-abc123","InstanceType":"t3.medium","RestoreTime":"2026-08-09T14:30:00Z"}' \
       --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
       --resource-type EC2
POST_VERIFY:
  - describe-restore-job returns Status COMPLETED, CreatedResourceArn
    set
  - Restored EC2 instance boots; verify via AWS Systems Manager
    Inventory or EC2 console
STATE: pending — COMPLETED within 5-15 min (PITR restore)
NOTES:
  - Restore creates a NEW EC2 instance with a new private IP. To
    preserve the original IP, stop the original instance first and
    specify the original private IP in metadata.
  - RestoreTime selects the moment within the 35-day PITR window. If
    omitted, restore uses the latest available recovery point.
```

## What the skill caught that a generic assistant misses

1. **Compliance vs governance mode:** A generic assistant omits the
   distinction or applies governance mode by default. The skill
   requires explicit mode selection and surfaces the
   `ChangeableForDays` grace window for COMPLIANCE mode.

2. **Retention window clamp:** A generic assistant sets
   `DeleteAfterDays` without checking against the vault's
   `MaxRetentionDays`. The skill blocks plans whose lifecycle exceeds
   the lock ceiling.

3. **PITR metadata:** A generic assistant omits `RestoreTime` or
   the required `InstanceId` / `SubnetId` for EC2 restore. The skill
   uses `get-recovery-point-restore-metadata` to populate the
   resource-type-specific template.

4. **Cross-region restore region:** A generic assistant attempts
   cross-region restore in the source region. The skill verifies the
   recovery point exists in the destination region and runs the CLI
   in the destination region.

5. **Grace window caveat:** A generic assistant omits that
   `ChangeableForDays` is the ONLY reversal window for COMPLIANCE
   mode. The skill surfaces the 72-hour grace explicitly.

6. **CONFIRM gate.** A generic assistant auto-executes. The skill
   emits `CONFIRM:` and waits — vault locks are irreversible after
   grace.

7. **KMS key policy verification:** A generic assistant assumes the
   KMS key works. The skill verifies `backup.<region>.amazonaws.com`
   has `kms:GenerateDataKey` / `kms:Decrypt` in the key policy.

8. **ContinuousBackup flag:** A generic assistant assumes
   point-in-time restore works on any recovery point. The skill
   verifies `ContinuousBackup: true` on the parent recovery point.

## Slash-command invocation

```
/aws:operate-backup-vault
```

Or via the orchestrator:

```
/aws:pipeline
You: "create a backup vault with compliance lock for CIS 3.6"
```

The orchestrator emits
`[Phase: Operate | Skills routed: backup-vault-operator]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "lock backup vault compliance mode"
# [Phase: Operate | Skills routed: backup-vault-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the vault is created and locked:

```bash
# Verify the vault lock is in COMPLIANCE mode
aws backup describe-backup-vault --backup-vault-name prod-compliance-vault \
  --profile default \
  --query 'VaultLock.{State:LockState,Mode:Mode,Min:MinRetentionDays,Max:MaxRetentionDays,Grace:ChangeableForDays}' \
  --output json

# Verify the backup plan is active
aws backup list-backup-plans --profile default \
  --query 'BackupPlansList[?BackupPlanName==`prod-daily-with-dr`].{Id:BackupPlanId,Name:BackupPlanName,Arn:BackupPlanArn}' \
  --output table

# Run a manual backup to verify the plan
aws backup start-backup-job --backup-vault-name prod-compliance-vault \
  --resource-arn arn:aws:ec2:us-east-1:111111111111:instance/i-0123456789abcdef0 \
  --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
  --idempotency-token "drill-$(date +%s)" \
  --profile default
```
