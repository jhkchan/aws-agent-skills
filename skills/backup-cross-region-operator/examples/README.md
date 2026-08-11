# End-to-end usage scenario: backup-cross-region-operator

A walkthrough showing the skill adding a cross-region copy rule to
a backup plan, starting a manual cross-region copy job, applying
a COMPLIANCE-mode DR vault lock in us-west-2, and running a
cross-region restore drill.

## Input (user prompt)

> Configure cross-region DR for our prod backup plan. Add a copy
> rule to plan `prod-daily-with-dr` in us-east-1 copying nightly
> recovery points to vault `dr-vault` in us-west-2 (KMS key xyz)
> with 90-day retention. Apply COMPLIANCE-mode vault lock on
> `dr-vault` in us-west-2 (MinRetentionDays=30, MaxRetentionDays=3650,
> ChangeableForDays=3) for CIS 3.6. Then start a manual cross-region
> copy of recovery point 1-2-3-4, and finally run a restore drill
> restoring to a new EC2 instance in us-west-2.

## Skill output — add-copy-rule

```text
OPERATION: add-copy-rule
VERDICT: READY
TARGET: prod-daily-vault (us-east-1) -> dr-vault (us-west-2)
PRE_CHECKS:
  - [PASS] Source vault prod-daily-vault exists in us-east-1
  - [PASS] Destination vault dr-vault exists in us-west-2
  - [PASS] Destination KMS key xyz Enabled, KeyManager CUSTOMER
  - [PASS] Destination KMS policy grants kms:GenerateDataKey,
    kms:Decrypt to backup.us-west-2.amazonaws.com
  - [PASS] DeleteAfterDays 90 <= MaxRetentionDays 3650
  - [PASS] Caller IAM role holds backup:CreateBackupPlan
STEPS:
  1. CONFIRM: About to add cross-region copy rule to plan
     prod-daily-with-dr in us-east-1. Recovery points will be
     copied to dr-vault in us-west-2 with 90-day retention.
     Proceed? (yes/no)
  2. aws backup create-backup-plan --backup-plan '{...}' --region us-east-1
POST_VERIFY:
  - describe-backup-plan returns CopyActions with destination us-west-2
  - First copy job runs at next schedule (cron 0 5 ? * * *)
STATE: pending — plan CREATED within ~10s; first cross-region copy
within 24h
NOTES:
  - Destination vault dr-vault is in us-west-2 — separate from
    source vault prod-daily-vault. Vault locks are independent.
  - Cross-region copy creates a NEW recovery point in dr-vault;
    does NOT replicate the source vault.
```

## Skill output — lock-dr-vault (COMPLIANCE mode)

```text
OPERATION: lock-dr-vault
VERDICT: READY
TARGET: dr-vault (us-west-2)
PRE_CHECKS:
  - [PASS] Vault dr-vault exists in us-west-2
  - [PASS] Vault currently UNLOCKED
  - [PASS] MinRetentionDays 30 <= MaxRetentionDays 3650
  - [PASS] ChangeableForDays 3 <= 3 max grace
STEPS:
  1. CONFIRM: About to apply COMPLIANCE-mode lock on dr-vault in
     us-west-2. After the 72-hour grace window, the lock CANNOT
     be removed even by root. Proceed? (yes/no)
  2. aws backup put-backup-vault-lock-configuration \
       --backup-vault-name dr-vault \
       --changeable-for-days 3 --min-retention-days 30 \
       --max-retention-days 3650 --region us-west-2
POST_VERIFY:
  - describe-backup-vault returns VaultLock.LockState LOCKED,
    Mode COMPLIANCE, MinRetentionDays 30, MaxRetentionDays 3650,
    ChangeableForDays 3
STATE: pending — lock active within ~30s; grace window starts
NOTES:
  - COMPLIANCE mode for CIS Benchmark 3.6. After grace, lock is
    irreversible. Independent of any source-region vault lock.
```

## Skill output — start-copy

```text
OPERATION: start-copy
VERDICT: READY
TARGET: recovery-point 1-2-3-4 (us-east-1) -> dr-vault (us-west-2)
PRE_CHECKS:
  - [PASS] Source recovery point 1-2-3-4 Status COMPLETED
  - [PASS] Destination vault dr-vault exists in us-west-2
  - [PASS] Source IAM role AWSBackupDefaultServiceRole holds
    backup:StartCopyJob
  - [PASS] Source KMS grants kms:Decrypt to backup.us-east-1
  - [PASS] Destination KMS grants kms:GenerateDataKey to backup.us-west-2
STEPS:
  1. CONFIRM: About to start-copy-job for recovery point 1-2-3-4
     from prod-daily-vault (us-east-1) to dr-vault (us-west-2).
     Proceed? (yes/no)
  2. aws backup start-copy-job --recovery-point-arn arn:aws:backup:us-east-1:111111111111:recovery-point:1-2-3-4 \
       --source-backup-vault-name prod-daily-vault \
       --destination-backup-vault-arn arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault \
       --iam-role-arn arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole \
       --idempotency-token 1723305600 --region us-east-1
POST_VERIFY:
  - describe-copy-job returns State COMPLETED within minutes to
    hours
  - list-recovery-points-by-backup-vault --backup-vault-name dr-vault
    --region us-west-2 shows the new recovery point
STATE: pending — copy job COMPLETED within minutes to hours
NOTES:
  - Same-account cross-region copy. KMS re-encryption is implicit.
  - Cost: per-GB-transferred + per-GB-stored in us-west-2.
```

## Skill output — start-cross-region-restore (COMPLETED)

```text
OPERATION: start-cross-region-restore
VERDICT: COMPLETED
TARGET: recovery-point 5-6-7-8 (us-west-2 dr-vault)
PRE_CHECKS:
  - [PASS] Recovery point exists in dr-vault in us-west-2
  - [PASS] Status COMPLETED
  - [PASS] Destination IAM role holds backup:StartRestoreJob,
    ec2:RunInstances, kms:Decrypt
  - [PASS] Destination KMS key grants kms:Decrypt to restore role
STEPS:
  1. (executed) aws backup start-restore-job --recovery-point-arn
    arn:aws:backup:us-west-2:111111111111:recovery-point:5-6-7-8
    --metadata {...} --resource-type EC2 --region us-west-2
POST_VERIFY:
  - [PASS] describe-restore-job returns Status COMPLETED
  - [PASS] CreatedResourceArn i-restored-xregion in us-west-2
  - [PASS] EC2 instance State running, LaunchTime 2026-08-09T16:35:02Z
STATE: COMPLETED — restored EC2 instance i-restored-xregion running
in us-west-2
NOTES:
  - Restore runs in the destination region (us-west-2). The
    restored EC2 instance has a new private IP.
  - Source region (us-east-1) is unaffected.
```

## What the skill caught that a generic assistant misses

1. **Destination vault + KMS verification:** A generic assistant
   omits checking the destination vault and KMS in the destination
   region. The skill verifies both before any copy.
2. **Vault lock independence:** A generic assistant assumes the
   source region's vault lock applies to the destination. The
   skill surfaces that each region's lock is independent.
3. **Cross-account Organizations requirement:** A generic assistant
   attempts cross-account copy without verifying org membership.
   The skill blocks if accounts are not in the same org.
4. **Destination region restore:** A generic assistant runs
   `start-restore-job` in the source region. The skill routes to
   the destination region.
5. **CONFIRM gate:** A generic assistant auto-executes. The skill
   emits CONFIRM and waits — DR vault locks are irreversible after
   grace.
6. **KMS ownership rationale:** A generic assistant omits who owns
   the KMS key. The skill surfaces same-account vs cross-account
   KMS ownership implications.
7. **Cost impact:** A generic assistant omits the per-GB-transferred
   cost. The skill surfaces it for large cross-region copies.

## Slash-command invocation

```
/aws:operate-backup-cross-region
```

Or via the orchestrator:

```
/aws:pipeline
You: "configure cross-region DR for prod backup plan with DR vault
      in us-west-2"
```

The orchestrator emits
`[Phase: Operate | Skills routed: backup-cross-region-operator]`
and hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "cross-region backup copy us-west-2"
# [Phase: Operate | Skills routed: backup-cross-region-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After adding the copy rule and applying the DR vault lock:

```bash
# Verify the DR vault lock is in COMPLIANCE mode in us-west-2
aws backup describe-backup-vault --backup-vault-name dr-vault \
  --profile default --region us-west-2 \
  --query 'VaultLock.{State:LockState,Mode:Mode,Min:MinRetentionDays,Max:MaxRetentionDays,Grace:ChangeableForDays}' \
  --output json

# Verify the backup plan has the cross-region copy rule
aws backup list-backup-plans --profile default \
  --query 'BackupPlansList[?BackupPlanName==`prod-daily-with-dr`].{Id:BackupPlanId,Name:BackupPlanName}' \
  --output table

# Verify copy jobs completed
aws backup list-copy-jobs --profile default --region us-east-1 \
  --by-state COMPLETED \
  --query 'CopyJobs[].{Id:CopyJobId,Src:SourceBackupVaultArn,Dst:DestinationBackupVaultArn,State:State}' \
  --output table
```
